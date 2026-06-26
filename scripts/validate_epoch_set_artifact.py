from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "work" / "release_evidence" / "p0_ui_only_runner" / "p0-ui-only-runner-evidence.json"
OUT_DIR = ROOT / "work" / "release_evidence" / "epoch_set_artifact_validator"
OUT_PATH = OUT_DIR / "epoch_set_artifact_validator.json"


FORBIDDEN_PATTERNS = [
    "diagnostic conclusion",
    "diagnostic result",
    "clinical diagnosis:",
    "clinical recommendation",
    "causal effect",
    "causal increase",
    "localized to",
    "brain activation",
    "precise brain region",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_manifest_path(source: Path) -> Path | None:
    if source.name.endswith(".json"):
        payload = load_json(source)
        if payload.get("protocol") == "QLANALYSER_P0_UI_ONLY_RUNNER":
            for item in payload.get("downloads") or []:
                if item.get("requirement") == "epoch_set_manifest.json":
                    candidate = Path(str(item.get("path") or ""))
                    if candidate.exists():
                        return candidate
            return None
        if payload.get("epoch_set_id") or payload.get("id"):
            return source
    return None


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EVIDENCE
    failures: list[dict] = []
    warnings: list[dict] = []

    if not source.exists():
        failures.append({"code": "SOURCE_MISSING", "detail": str(source)})
        manifest_path = None
        manifest = {}
    else:
        manifest_path = find_manifest_path(source)
        if manifest_path is None:
            failures.append({"code": "EPOCH_MANIFEST_NOT_FOUND", "detail": str(source)})
            manifest = {}
        else:
            manifest = load_json(manifest_path)

    text_blob = json.dumps(manifest, ensure_ascii=False).lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in text_blob:
            failures.append({"code": "FORBIDDEN_EPOCH_CLAIM", "detail": pattern})

    if manifest:
        if manifest.get("schema_version") == "qlanalyser-epoch-set-manifest-draft-v0.1":
            failures.append({"code": "EPOCH_SET_STILL_DRAFT", "detail": manifest.get("schema_version")})
        if manifest.get("persisted") is not True:
            failures.append({"code": "EPOCH_SET_NOT_PERSISTED", "detail": manifest.get("persisted")})
        if not (manifest.get("epoch_set_id") or manifest.get("id")):
            failures.append({"code": "EPOCH_SET_ID_MISSING", "detail": None})
        if not isinstance(manifest.get("revision"), int) or manifest.get("revision") < 1:
            failures.append({"code": "EPOCH_SET_REVISION_INVALID", "detail": manifest.get("revision")})
        if manifest.get("status") not in {"draft", "confirmed"}:
            failures.append({"code": "EPOCH_SET_STATUS_INVALID", "detail": manifest.get("status")})
        if not isinstance(manifest.get("event_mapping"), list) or len(manifest.get("event_mapping") or []) < 2:
            failures.append({"code": "EVENT_MAPPING_INCOMPLETE", "detail": manifest.get("event_mapping")})
        if "not for clinical diagnosis" not in str(manifest.get("boundary", "")).lower():
            failures.append({"code": "NON_DIAGNOSTIC_BOUNDARY_MISSING", "detail": manifest.get("boundary")})
        if "sensor-space" not in str(manifest.get("boundary", "")).lower():
            failures.append({"code": "SENSOR_SPACE_BOUNDARY_MISSING", "detail": manifest.get("boundary")})
        lineage = manifest.get("lineage_json") or {}
        for key in ["data_preparation_plan_id", "data_preparation_revision", "source_file_id", "audit_trace_id"]:
            if key not in lineage:
                failures.append({"code": "LINEAGE_FIELD_MISSING", "detail": key})
        artifact_root_value = str(manifest.get("artifact_root") or "")
        artifact_root = Path(artifact_root_value)
        if not artifact_root_value or not artifact_root.exists():
            failures.append({"code": "ARTIFACT_ROOT_MISSING", "detail": artifact_root_value})
        else:
            for relative in [
                "reproducibility/epoch_set_manifest.json",
                "reproducibility/epoch_set_artifact_contract.json",
                "manifest.json",
            ]:
                path = artifact_root / relative
                if not path.exists():
                    failures.append({"code": "ARTIFACT_FILE_MISSING", "detail": str(path)})
            stored_manifest = artifact_root / "reproducibility" / "epoch_set_manifest.json"
            if stored_manifest.exists():
                stored = load_json(stored_manifest)
                if stored.get("id") != manifest.get("id"):
                    failures.append({"code": "STORED_MANIFEST_ID_MISMATCH", "detail": {"download": manifest.get("id"), "stored": stored.get("id")}})

    output = {
        "schema_version": "qlanalyser-epoch-set-artifact-validator-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(source),
        "manifest_path": str(manifest_path) if manifest_path else None,
        "status": "passed" if not failures else "failed",
        "decision": "pass" if not failures else "block",
        "checks": {
            "persisted": manifest.get("persisted") is True if manifest else False,
            "has_revision": isinstance(manifest.get("revision"), int) if manifest else False,
            "has_lineage": bool((manifest.get("lineage_json") or {}).get("data_preparation_plan_id")) if manifest else False,
            "has_artifact_root": bool(manifest.get("artifact_root")) if manifest else False,
            "non_diagnostic_boundary": "not for clinical diagnosis" in str(manifest.get("boundary", "")).lower() if manifest else False,
            "sensor_space_boundary": "sensor-space" in str(manifest.get("boundary", "")).lower() if manifest else False,
        },
        "failures": failures,
        "warnings": warnings,
        "important_boundary": "This validates epoch_set artifact shape and boundary wording. It does not validate EEG method correctness or product release readiness.",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
