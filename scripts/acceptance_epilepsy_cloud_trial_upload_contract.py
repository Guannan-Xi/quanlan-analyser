from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app  # noqa: E402


EVIDENCE_DIR = ROOT / "work" / "release_evidence" / "20260629-epilepsy-cloud-trial-v0-1-upload-contract"
EVIDENCE_PATH = EVIDENCE_DIR / "upload_authorization_contract.json"
FIXTURE_PATH = ROOT / "work" / "fixtures" / "epilepsy_regular_labeled" / "regular_epilepsy_labeled_60s.edf"


def ensure_fixture() -> None:
    if FIXTURE_PATH.exists():
        return
    from scripts.generate_regular_epilepsy_labeled_fixture import main as generate_fixture

    generate_fixture()


def main() -> None:
    ensure_fixture()
    client = TestClient(app)
    project_response = client.post(
        "/api/projects",
        json={
            "name": "Epilepsy cloud trial upload contract",
            "description": "P0 upload authorization acceptance",
            "research_type": "epilepsy_cloud_trial_v0_1",
        },
    )
    project_response.raise_for_status()
    project = project_response.json()

    with FIXTURE_PATH.open("rb") as handle:
        rejected = client.post(
            f"/api/eeg/upload?project_id={project['id']}",
            files={"file": (FIXTURE_PATH.name, handle, "application/octet-stream")},
        )

    authorization_text = "Uploader confirms authorized research trial upload for epilepsy-like candidate event screening."
    with FIXTURE_PATH.open("rb") as handle:
        accepted = client.post(
            f"/api/eeg/upload?project_id={project['id']}&upload_authorization_confirmed=true&upload_authorization_text={authorization_text}",
            files={"file": (FIXTURE_PATH.name, handle, "application/octet-stream")},
        )
    accepted.raise_for_status()
    eeg_file = accepted.json()

    metadata_response = client.get(f"/api/eeg/files/{eeg_file['id']}/metadata")
    metadata_response.raise_for_status()
    metadata = metadata_response.json()

    checks = {
        "unauthorized_upload_rejected": rejected.status_code == 422 and "UPLOAD_AUTHORIZATION_REQUIRED" in rejected.text,
        "authorized_upload_accepted": accepted.status_code == 200,
        "file_authorization_flag_true": eeg_file.get("upload_authorization_confirmed") is True,
        "file_authorization_text_stored": authorization_text in str(eeg_file.get("upload_authorization_text") or ""),
        "metadata_authorization_flag_true": metadata.get("upload_authorization_confirmed") is True,
        "metadata_readable": metadata.get("status") == "readable",
        "metadata_has_channels": bool(metadata.get("channel_names")) and int(metadata.get("channel_count") or 0) >= 1,
        "metadata_has_duration_and_sfreq": float(metadata.get("duration_sec") or 0) > 0 and float(metadata.get("sampling_rate") or 0) > 0,
        "format_is_edf": str(eeg_file.get("detected_format") or "").lower() == "edf",
    }
    evidence = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "fixture_path": str(FIXTURE_PATH),
        "project_id": project["id"],
        "file_id": eeg_file["id"],
        "checks": checks,
        "rejected_status_code": rejected.status_code,
        "rejected_body": rejected.json() if rejected.headers.get("content-type", "").startswith("application/json") else rejected.text,
        "eeg_file_snapshot": {
            "id": eeg_file.get("id"),
            "original_filename": eeg_file.get("original_filename"),
            "detected_format": eeg_file.get("detected_format"),
            "size_bytes": eeg_file.get("size_bytes"),
            "duration_sec": eeg_file.get("duration_sec"),
            "sampling_rate": eeg_file.get("sampling_rate"),
            "channel_count": eeg_file.get("channel_count"),
            "upload_authorization_confirmed": eeg_file.get("upload_authorization_confirmed"),
            "upload_authorization_confirmed_at": eeg_file.get("upload_authorization_confirmed_at"),
        },
        "metadata_snapshot": {
            "status": metadata.get("status"),
            "format": metadata.get("format"),
            "duration_sec": metadata.get("duration_sec"),
            "sampling_rate": metadata.get("sampling_rate"),
            "channel_count": metadata.get("channel_count"),
            "channel_names": metadata.get("channel_names"),
            "upload_authorization_confirmed": metadata.get("upload_authorization_confirmed"),
        },
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    if evidence["status"] != "PASS":
        raise SystemExit(json.dumps(evidence, ensure_ascii=False, indent=2))
    print(json.dumps({"status": "PASS", "evidence": str(EVIDENCE_PATH)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
