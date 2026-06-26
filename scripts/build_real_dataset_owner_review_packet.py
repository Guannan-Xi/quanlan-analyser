from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "work" / "release_evidence" / "07-full-product-e2e-pdca" / "11_real_dataset_owner_review"
INPUT_GATE_DIR = EVIDENCE_ROOT / "01_input_gate"
OWNER_DIR = EVIDENCE_ROOT / "05_owner_packet"
TEMPLATE_PATH = EVIDENCE_ROOT / "input_manifest.template.json"
DEFAULT_MANIFEST_PATH = EVIDENCE_ROOT / "input_manifest.json"
CHECKLIST_PATH = INPUT_GATE_DIR / "owner_input_checklist.md"
CANDIDATE_INVENTORY_PATH = INPUT_GATE_DIR / "candidate_data_inventory.json"
PREFLIGHT_PATH = INPUT_GATE_DIR / "real_dataset_owner_review_preflight.json"
FINAL_RECEIPT_PATH = OWNER_DIR / "real_dataset_owner_review_final_receipt.json"

DOCS = [
    ROOT / "docs" / "product" / "qlanalyser_real_dataset_owner_review_requirements_20260626.md",
    ROOT / "docs" / "product" / "qlanalyser_real_dataset_owner_review_design_20260626.md",
    ROOT / "docs" / "product" / "qlanalyser_real_dataset_owner_review_test_plan_20260626.md",
]

ALLOWED_EXTENSIONS = {".edf", ".fif", ".set"}
SYNTHETIC_MARKERS = {
    "synthetic",
    "demo",
    "teaching",
    "fixture",
    "sample",
    "ui_",
    "p0_",
    "test",
    "delete_target",
    "oddball",
}
PII_PATH_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    re.compile(r"\b1[3-9]\d{9}\b"),
    re.compile(r"\b(19|20)\d{2}[-_./]?(0[1-9]|1[0-2])[-_./]?([0-2]\d|3[01])\b"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except (ValueError, OSError):
        return str(path).replace("\\", "/")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path, limit_mb: int = 128) -> str | None:
    if path.stat().st_size > limit_mb * 1024 * 1024:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_candidate(path: Path) -> dict[str, Any]:
    text = str(path).lower()
    markers = sorted(marker for marker in SYNTHETIC_MARKERS if marker in text)
    pii_hits = [pattern.pattern for pattern in PII_PATH_PATTERNS if pattern.search(str(path))]
    return {
        "path": rel(path),
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "sha256_if_small": sha256_file(path),
        "synthetic_or_test_markers": markers,
        "path_privacy_risk_patterns": pii_hits,
        "owner_authorized": False,
        "eligibility": "candidate_only_manifest_required",
        "note": "Local discovery is inventory only; owner manifest is required before regression use.",
    }


def scan_candidates(limit: int = 200) -> list[dict[str, Any]]:
    roots = [ROOT / "data", ROOT / "work"]
    candidates: list[Path] = []
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if len(candidates) >= limit:
                break
            if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
                candidates.append(path)
    return [classify_candidate(path) for path in sorted(candidates)]


def manifest_template() -> dict[str, Any]:
    return {
        "owner_confirmed_authorized": False,
        "owner": "",
        "authorization_note": "",
        "datasets": [
            {
                "dataset_id": "owner_review_001",
                "path": "",
                "data_type": "edf",
                "anonymized": False,
                "contains_phi": "unknown",
                "allowed_methods": [
                    "qc",
                    "psd",
                    "erp",
                    "tfr",
                    "multitaper_psd",
                    "multitaper_tfr",
                    "reference_csd",
                    "pac",
                    "connectivity",
                ],
                "event_markers_available": "unknown",
                "channel_location_available": "unknown",
                "known_limitations": [],
            }
        ],
    }


def load_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(path: Path) -> dict[str, Any]:
    manifest = load_manifest(path)
    blockers: list[str] = []
    warnings: list[str] = []
    datasets_out: list[dict[str, Any]] = []
    if manifest is None:
        return {
            "status": "blocked",
            "manifest_path": rel(path),
            "exists": False,
            "blockers": ["input_manifest.json is missing"],
            "warnings": [],
            "datasets": [],
        }

    if manifest.get("owner_confirmed_authorized") is not True:
        blockers.append("owner_confirmed_authorized must be true")
    if not str(manifest.get("owner", "")).strip():
        blockers.append("owner is required")
    if not str(manifest.get("authorization_note", "")).strip():
        blockers.append("authorization_note is required")

    datasets = manifest.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        blockers.append("datasets must contain at least one dataset")
        datasets = []

    for index, item in enumerate(datasets):
        row_blockers: list[str] = []
        dataset_id = str(item.get("dataset_id") or f"dataset_{index + 1}")
        raw_path = str(item.get("path", "")).strip()
        file_path = Path(raw_path) if raw_path else Path()
        if not raw_path:
            row_blockers.append("path is required")
        elif not file_path.exists():
            row_blockers.append("path does not exist")
        elif file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            row_blockers.append(f"unsupported extension {file_path.suffix}")
        if item.get("anonymized") is not True:
            row_blockers.append("anonymized must be true")
        if item.get("contains_phi") is not False:
            row_blockers.append("contains_phi must be false")
        allowed_methods = item.get("allowed_methods")
        if not isinstance(allowed_methods, list) or not allowed_methods:
            row_blockers.append("allowed_methods must be a non-empty list")
        pii_hits = [pattern.pattern for pattern in PII_PATH_PATTERNS if pattern.search(raw_path)]
        if pii_hits:
            row_blockers.append("path appears to contain privacy-risk tokens")

        blockers.extend([f"{dataset_id}: {message}" for message in row_blockers])
        if raw_path and file_path.exists():
            dataset_record = {
                "dataset_id": dataset_id,
                "path_alias": file_path.name,
                "path": rel(file_path),
                "extension": file_path.suffix.lower(),
                "size_bytes": file_path.stat().st_size,
                "sha256_if_small": sha256_file(file_path),
                "allowed_methods": allowed_methods,
                "event_markers_available": item.get("event_markers_available"),
                "channel_location_available": item.get("channel_location_available"),
                "known_limitations": item.get("known_limitations", []),
                "eligible": not row_blockers,
            }
        else:
            dataset_record = {
                "dataset_id": dataset_id,
                "path_alias": "",
                "path": raw_path,
                "eligible": False,
                "allowed_methods": allowed_methods,
                "known_limitations": item.get("known_limitations", []),
            }
        datasets_out.append(dataset_record)

    return {
        "status": "passed" if not blockers else "blocked",
        "manifest_path": rel(path),
        "exists": True,
        "blockers": blockers,
        "warnings": warnings,
        "datasets": datasets_out,
    }


def render_checklist(preflight: dict[str, Any]) -> str:
    lines = [
        "# QLanalyser Real Dataset Owner Input Checklist",
        "",
        f"Generated: {utc_now()}",
        "",
        "This checklist is required before real or representative anonymized datasets can be used for QLanalyser regression.",
        "",
        "## Current Status",
        "",
        f"- Input gate status: `{preflight['status']}`",
        f"- Final receipt: `{preflight['final_receipt_type']}`",
        f"- Manifest template: `{rel(TEMPLATE_PATH)}`",
        f"- Active manifest: `{rel(DEFAULT_MANIFEST_PATH)}`",
        "",
        "## Owner Inputs Needed",
        "",
    ]
    if preflight["blockers"]:
        lines.extend([f"- {item}" for item in preflight["blockers"]])
    else:
        lines.append("- No input-gate blockers remain. Continue to real-dataset regression run.")
    lines.extend(
        [
            "",
            "## Required Manifest Fields",
            "",
            "- `owner_confirmed_authorized: true`",
            "- `owner`",
            "- `authorization_note`",
            "- for every dataset: existing `path`, `anonymized: true`, `contains_phi: false`, and explicit `allowed_methods`",
            "",
            "## Safety Rule",
            "",
            "Local files found in `data/` or `work/` are inventory only. They are not real-dataset regression inputs until the owner manifest authorizes them.",
            "",
            "## Next Command After Manifest Is Ready",
            "",
            "```powershell",
            "python -X utf8 scripts/build_real_dataset_owner_review_packet.py --input-manifest work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the QLanalyser real-dataset owner review input-gate packet.")
    parser.add_argument("--input-manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--candidate-limit", type=int, default=200)
    args = parser.parse_args()

    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    INPUT_GATE_DIR.mkdir(parents=True, exist_ok=True)
    OWNER_DIR.mkdir(parents=True, exist_ok=True)
    if not TEMPLATE_PATH.exists():
        write_json(TEMPLATE_PATH, manifest_template())

    candidates = scan_candidates(limit=args.candidate_limit)
    write_json(
        CANDIDATE_INVENTORY_PATH,
        {
            "status": "prepared",
            "generated_at": utc_now(),
            "candidate_count": len(candidates),
            "candidates": candidates,
            "rule": "Candidates are not owner-authorized real data until input_manifest.json says so.",
        },
    )

    manifest_result = validate_manifest(Path(args.input_manifest))
    docs_status = [
        {"path": rel(path), "exists": path.exists(), "status": "passed" if path.exists() else "missing"}
        for path in DOCS
    ]
    blockers = []
    blockers.extend([f"doc missing: {item['path']}" for item in docs_status if not item["exists"]])
    blockers.extend(manifest_result["blockers"])
    status = "passed" if not blockers else "blocked"
    final_receipt_type = "completed_final_receipt" if status == "passed" else "blocked_final_receipt"
    preflight = {
        "status": status,
        "generated_at": utc_now(),
        "pdca": {
            "plan": "Create owner-authorized real-dataset regression input gate.",
            "do": "Write manifest template, scan local candidates as inventory, validate input_manifest.json.",
            "check": "Docs exist, candidate inventory exists, owner manifest authorizes anonymized data before use.",
            "act": "Proceed to regression if passed; otherwise block with exact owner inputs needed.",
        },
        "docs": docs_status,
        "manifest_validation": manifest_result,
        "candidate_inventory": rel(CANDIDATE_INVENTORY_PATH),
        "candidate_count": len(candidates),
        "blockers": blockers,
        "final_receipt_type": final_receipt_type,
        "next_real_artifact": "authorized_real_dataset_regression_run",
    }
    write_json(PREFLIGHT_PATH, preflight)
    CHECKLIST_PATH.write_text(render_checklist(preflight), encoding="utf-8")

    final_receipt = {
        "status": final_receipt_type,
        "generated_at": utc_now(),
        "blocked": bool(blockers),
        "summary": (
            "Real-dataset owner input gate passed; regression can start."
            if not blockers
            else "Real-dataset regression is blocked until owner manifest authorizes anonymized datasets."
        ),
        "evidence": {
            "preflight": rel(PREFLIGHT_PATH),
            "candidate_inventory": rel(CANDIDATE_INVENTORY_PATH),
            "owner_input_checklist": rel(CHECKLIST_PATH),
            "input_manifest_template": rel(TEMPLATE_PATH),
        },
        "blockers": blockers,
        "route_chain": "Synthetic full-product acceptance -> real-dataset owner input gate -> authorized regression run -> owner release review",
        "boundary": "No local EEG file is treated as real-data evidence without owner authorization and anonymization confirmation.",
    }
    write_json(FINAL_RECEIPT_PATH, final_receipt)

    print(
        json.dumps(
            {
                "status": final_receipt_type,
                "preflight": rel(PREFLIGHT_PATH),
                "checklist": rel(CHECKLIST_PATH),
                "candidate_count": len(candidates),
                "blockers": blockers,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
