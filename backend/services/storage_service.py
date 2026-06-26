from pathlib import Path

from fastapi import HTTPException, UploadFile

from backend.models.eeg_file import EEGFileRead
from backend.models.base import new_id, utc_now
from backend.models.project import ProjectCreate, ProjectRead, ProjectUpdate
from backend.models.subject import SubjectCreate, SubjectRead
from backend.services import audit_service, object_storage_service, quota_service, state_store

ROOT = Path(__file__).resolve().parents[2]
UPLOAD_ROOT = ROOT / "data" / "uploads"

_projects: dict[str, ProjectRead] = state_store.load_registry("projects", ProjectRead)
_subjects: dict[str, SubjectRead] = state_store.load_registry("subjects", SubjectRead)
_eeg_files: dict[str, EEGFileRead] = state_store.load_registry("eeg_files", EEGFileRead)

PROTECTED_TEACHING_PROJECT_IDS = {"proj_demo_learning", "proj_demo_epilepsy_lab"}
PROTECTED_TEACHING_FILE_IDS = {"eeg_demo_teaching_oddball", "eeg_demo_epilepsy_high_amplitude"}
PROTECTED_TEACHING_RETENTION_POLICY = "protected_teaching_demo"


def _refresh_projects() -> None:
    _projects.clear()
    _projects.update(state_store.load_registry("projects", ProjectRead))


def _refresh_subjects() -> None:
    _subjects.clear()
    _subjects.update(state_store.load_registry("subjects", SubjectRead))


def _refresh_eeg_files() -> None:
    _eeg_files.clear()
    _eeg_files.update(state_store.load_registry("eeg_files", EEGFileRead))


def _save_projects() -> None:
    for project in _projects.values():
        state_store.upsert_item("projects", project)


def _save_subjects() -> None:
    for subject in _subjects.values():
        state_store.upsert_item("subjects", subject)


def _save_eeg_files() -> None:
    for eeg_file in _eeg_files.values():
        state_store.upsert_item("eeg_files", eeg_file)


def _is_protected_teaching_project(project: ProjectRead | None) -> bool:
    if not project:
        return False
    policy = project.permission_policy or {}
    return bool(
        project.id in PROTECTED_TEACHING_PROJECT_IDS
        or policy.get("protected_teaching_dataset")
        or policy.get("teaching_mode")
    )


def _is_protected_teaching_file(eeg_file: EEGFileRead | None) -> bool:
    if not eeg_file:
        return False
    metadata = eeg_file.metadata_json or {}
    policy = eeg_file.permission_policy or {}
    return bool(
        eeg_file.id in PROTECTED_TEACHING_FILE_IDS
        or eeg_file.project_id in PROTECTED_TEACHING_PROJECT_IDS
        or metadata.get("protected_teaching_dataset")
        or policy.get("protected_teaching_dataset")
        or metadata.get("teaching_mode")
        or policy.get("teaching_mode")
        or eeg_file.retention_policy == PROTECTED_TEACHING_RETENTION_POLICY
    )


def _raise_teaching_protected(object_type: str, object_id: str) -> None:
    raise HTTPException(
        status_code=409,
        detail={
            "code": "TEACHING_DATASET_PROTECTED",
            "message": "Teaching data is built in for guided practice and cannot be deleted, archived, renamed, or overwritten.",
            "object_type": object_type,
            "object_id": object_id,
        },
    )


def create_project(payload: ProjectCreate) -> ProjectRead:
    project = ProjectRead(**payload.model_dump())
    _projects[project.id] = project
    state_store.upsert_item("projects", project)
    return project


def upsert_project(project: ProjectRead) -> ProjectRead:
    _projects[project.id] = project
    state_store.upsert_item("projects", project)
    return project


def list_projects() -> list[ProjectRead]:
    _refresh_projects()
    return list(_projects.values())


def get_project(project_id: str) -> ProjectRead:
    _refresh_projects()
    try:
        return _projects[project_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


def update_project(project_id: str, payload: ProjectUpdate) -> ProjectRead:
    project = get_project(project_id)
    if _is_protected_teaching_project(project):
        _raise_teaching_protected("project", project.id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if value is not None and hasattr(project, key):
            setattr(project, key, value)
    project.updated_at = utc_now()
    if payload.updated_by:
        project.updated_by = payload.updated_by
    elif not project.updated_by:
        project.updated_by = payload.updated_by or "local-user"
    _projects[project.id] = project
    state_store.upsert_item("projects", project)
    audit_service.record_event(
        action="project.updated",
        object_type="project",
        object_id=project.id,
        organization_id=project.organization_id,
        project_id=project.id,
        actor_user_id=project.updated_by or project.owner_user_id,
        metadata_json={"updated_fields": sorted(data.keys())},
    )
    return project


def archive_project(project_id: str, actor_user_id: str = "local-user") -> ProjectRead:
    project = get_project(project_id)
    if _is_protected_teaching_project(project):
        _raise_teaching_protected("project", project.id)
    project.status = "archived"
    project.updated_by = actor_user_id
    project.updated_at = utc_now()
    _projects[project.id] = project
    state_store.upsert_item("projects", project)
    audit_service.record_event(
        action="project.archived",
        object_type="project",
        object_id=project.id,
        organization_id=project.organization_id,
        project_id=project.id,
        actor_user_id=actor_user_id,
        metadata_json={"delete_mode": "not_deleted", "status": "archived"},
    )
    return project


def create_subject(project_id: str, payload: SubjectCreate) -> SubjectRead:
    get_project(project_id)
    subject = SubjectRead(project_id=project_id, **payload.model_dump())
    _subjects[subject.id] = subject
    state_store.upsert_item("subjects", subject)
    return subject


def list_subjects(project_id: str) -> list[SubjectRead]:
    get_project(project_id)
    _refresh_subjects()
    return [subject for subject in _subjects.values() if subject.project_id == project_id]


async def create_eeg_file(project_id: str, subject_id: str | None, upload: UploadFile | None) -> EEGFileRead:
    project = get_project(project_id)
    _refresh_subjects()
    if subject_id and subject_id not in _subjects:
        raise HTTPException(status_code=404, detail="Subject not found")
    if upload is None or not upload.filename:
        raise HTTPException(status_code=422, detail="A real EEG file upload is required")

    filename = Path(upload.filename).name
    suffix = Path(filename).suffix.lower().lstrip(".") or "unknown"
    if suffix not in {"edf", "bdf", "set", "vhdr", "cnt", "fif"}:
        raise HTTPException(status_code=422, detail=f"Unsupported EEG file format: {suffix}")

    file_id = new_id("eeg")
    object_key = f"uploads/{project_id}/{file_id}/{filename}"
    upload_status = "uploading"
    try:
        stored_object = await object_storage_service.put_upload_file_stream(
            upload,
            object_key,
            metadata={"project_id": project_id, "subject_id": subject_id, "original_filename": filename},
        )
        upload_status = "uploaded"
    except HTTPException:
        upload_status = "failed"
        raise

    eeg_file = EEGFileRead(
        id=file_id,
        organization_id=project.organization_id,
        project_id=project_id,
        subject_id=subject_id,
        original_filename=filename,
        stored_path=Path(stored_object["path"]),
        detected_format=suffix,
        object_key=stored_object["object_key"],
        storage_backend=stored_object["storage_backend"],
        storage_tier="hot",
        size_bytes=stored_object["size_bytes"],
        sha256=stored_object["sha256"],
        content_type=stored_object.get("content_type"),
        status=upload_status,
        upload_status=upload_status,
        owner_user_id=project.owner_user_id,
        created_by=project.owner_user_id,
        quota_account_id=project.quota_account_id,
        updated_at=utc_now(),
    )
    try:
        from backend.services import metadata_service

        metadata_service.extract_metadata(eeg_file)
        eeg_file.metadata_extracted_at = utc_now()
        eeg_file.status = "metadata_ready"
    except Exception as exc:
        eeg_file.metadata_json.update(
            {
                "metadata_status": "metadata_extraction_failed",
                "metadata_error": str(exc),
                "filename": filename,
                "format": suffix,
            }
        )
    audit = audit_service.record_event(
        action="eeg_file.uploaded",
        object_type="eeg_file",
        object_id=eeg_file.id,
        organization_id=eeg_file.organization_id,
        project_id=eeg_file.project_id,
        actor_user_id=eeg_file.owner_user_id,
        metadata_json={
            "object_key": eeg_file.object_key,
            "size_bytes": eeg_file.size_bytes,
            "sha256": eeg_file.sha256,
            "upload_status": eeg_file.upload_status,
        },
    )
    eeg_file.audit_trace_id = audit.audit_trace_id
    quota_service.record_usage(
        resource_type="storage_bytes_hot",
        action="eeg_file.uploaded",
        quantity=float(eeg_file.size_bytes or 0),
        unit="bytes",
        source_type="eeg_file",
        source_id=eeg_file.id,
        organization_id=eeg_file.organization_id,
        project_id=eeg_file.project_id,
        owner_user_id=eeg_file.owner_user_id,
        quota_account_id=eeg_file.quota_account_id,
        metadata_json=quota_service.upload_quota_preview(eeg_file.size_bytes),
    )
    _eeg_files[eeg_file.id] = eeg_file
    state_store.upsert_item("eeg_files", eeg_file)
    return eeg_file


def register_eeg_file(eeg_file: EEGFileRead) -> EEGFileRead:
    get_project(eeg_file.project_id)
    _eeg_files[eeg_file.id] = eeg_file
    state_store.upsert_item("eeg_files", eeg_file)
    return eeg_file


def list_eeg_files() -> list[EEGFileRead]:
    _refresh_eeg_files()
    return list(_eeg_files.values())


def get_eeg_file(file_id: str) -> EEGFileRead:
    _refresh_eeg_files()
    try:
        return _eeg_files[file_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="EEG file not found") from exc


def update_eeg_file_label(file_id: str, label: str) -> dict:
    file = get_eeg_file(file_id)
    if _is_protected_teaching_file(file):
        _raise_teaching_protected("eeg_file", file.id)
    file.metadata_json["label"] = label
    _eeg_files[file_id] = file
    state_store.upsert_item("eeg_files", file)
    return {"id": file_id, "label": label, "status": "updated"}


def delete_eeg_file(file_id: str) -> None:
    eeg_file = get_eeg_file(file_id)
    if _is_protected_teaching_file(eeg_file):
        _raise_teaching_protected("eeg_file", eeg_file.id)
    eeg_file.status = "deleted"
    eeg_file.upload_status = "deleted"
    eeg_file.deleted_at = utc_now()
    eeg_file.updated_at = utc_now()
    _eeg_files[file_id] = eeg_file
    state_store.upsert_item("eeg_files", eeg_file)
    audit_service.record_event(
        action="eeg_file.soft_deleted",
        object_type="eeg_file",
        object_id=eeg_file.id,
        organization_id=eeg_file.organization_id,
        project_id=eeg_file.project_id,
        actor_user_id=eeg_file.owner_user_id,
        metadata_json={"retention_policy": eeg_file.retention_policy},
    )
