from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import lab_demo_service, storage_service


async def main() -> int:
    dataset = lab_demo_service.ensure_epilepsy_demo_dataset()
    project_id = dataset["project"]["id"]
    file_id = dataset["file"]["id"]

    checks: dict[str, bool] = {
        "epilepsy_demo_project": project_id == "proj_demo_epilepsy_lab",
        "epilepsy_demo_file": file_id == "eeg_demo_epilepsy_high_amplitude",
    }

    try:
        await storage_service.create_eeg_file(project_id, subject_id=None, upload=None)
        checks["upload_to_protected_project_blocked"] = False
    except HTTPException as exc:
        checks["upload_to_protected_project_blocked"] = exc.status_code == 409 and (exc.detail or {}).get("code") == "TEACHING_DATASET_PROTECTED"

    try:
        storage_service.update_eeg_file_label(file_id, "should-not-change")
        checks["rename_protected_file_blocked"] = False
    except HTTPException as exc:
        checks["rename_protected_file_blocked"] = exc.status_code == 409 and (exc.detail or {}).get("code") == "TEACHING_DATASET_PROTECTED"

    try:
        storage_service.delete_eeg_file(file_id)
        checks["delete_protected_file_blocked"] = False
    except HTTPException as exc:
        checks["delete_protected_file_blocked"] = exc.status_code == 409 and (exc.detail or {}).get("code") == "TEACHING_DATASET_PROTECTED"

    print({"status": "passed" if all(checks.values()) else "failed", "checks": checks})
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
