from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def expect_http_error(label: str, status_code: int, fn) -> None:
    try:
        fn()
    except HTTPException as exc:
        if exc.status_code != status_code:
            raise AssertionError(f"{label}: expected HTTP {status_code}, got {exc.status_code}") from exc
        return
    raise AssertionError(f"{label}: expected HTTP {status_code}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qlanalyser-subject-ownership-") as tmp:
        os.environ["QLANALYSER_STATE_ROOT"] = str(Path(tmp) / "state")
        from backend.models.project import ProjectCreate
        from backend.models.subject import SubjectCreate
        from backend.services import storage_service

        importlib.reload(storage_service)

        project_a = storage_service.create_project(
            ProjectCreate(
                name="Owner A project",
                owner_user_id="owner-a",
                created_by="owner-a",
            )
        )
        project_b = storage_service.create_project(
            ProjectCreate(
                name="Owner B project",
                owner_user_id="owner-b",
                created_by="owner-b",
            )
        )
        subject_a = storage_service.create_subject(
            project_a.id,
            SubjectCreate(subject_code="sub-a"),
            requesting_user_id="owner-a",
        )
        subject_b = storage_service.create_subject(
            project_b.id,
            SubjectCreate(subject_code="sub-b"),
            requesting_user_id="owner-b",
        )

        visible_to_a = storage_service.list_subjects(project_a.id, requesting_user_id="owner-a")
        assert any(item.id == subject_a.id for item in visible_to_a), "owner A should list own subject"

        expect_http_error(
            "owner B cannot list owner A subjects",
            403,
            lambda: storage_service.list_subjects(project_a.id, requesting_user_id="owner-b"),
        )
        expect_http_error(
            "owner B cannot create subject under owner A project",
            403,
            lambda: storage_service.create_subject(
                project_a.id,
                SubjectCreate(subject_code="sub-b-under-a"),
                requesting_user_id="owner-b",
            ),
        )
        expect_http_error(
            "upload cannot reference subject from another project",
            403,
            lambda: storage_service.assert_subject_belongs_to_project(subject_b.id, project_a.id),
        )

    print("PASS subject project ownership isolation")


if __name__ == "__main__":
    main()
