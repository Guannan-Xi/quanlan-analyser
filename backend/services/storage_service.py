from pathlib import Path

from fastapi import HTTPException, UploadFile

from backend.models.eeg_file import EEGFileRead
from backend.models.project import ProjectCreate, ProjectRead
from backend.models.subject import SubjectCreate, SubjectRead
from backend.services import state_store

ROOT = Path(__file__).resolve().parents[2]
UPLOAD_ROOT = ROOT / "data" / "uploads"

_projects: dict[str, ProjectRead] = state_store.load_registry("projects", ProjectRead)
_subjects: dict[str, SubjectRead] = state_store.load_registry("subjects", SubjectRead)
_eeg_files: dict[str, EEGFileRead] = state_store.load_registry("eeg_files", EEGFileRead)


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


def create_project(payload: ProjectCreate) -> ProjectRead:
    project = ProjectRead(**payload.model_dump())
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
    get_project(project_id)
    _refresh_subjects()
    if subject_id and subject_id not in _subjects:
        raise HTTPException(status_code=404, detail="Subject not found")
    if upload is None or not upload.filename:
        raise HTTPException(status_code=422, detail="A real EEG file upload is required")

    filename = Path(upload.filename).name
    suffix = Path(filename).suffix.lower().lstrip(".") or "unknown"
    if suffix not in {"edf", "bdf", "set", "vhdr", "cnt", "fif"}:
        raise HTTPException(status_code=422, detail=f"Unsupported EEG file format: {suffix}")

    content = await upload.read()
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded EEG file is empty")

    project_dir = UPLOAD_ROOT / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    stored_path = project_dir / filename
    stored_path.write_bytes(content)

    eeg_file = EEGFileRead(
        project_id=project_id,
        subject_id=subject_id,
        original_filename=filename,
        stored_path=stored_path,
        detected_format=suffix,
    )
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
    file.metadata_json["label"] = label
    _eeg_files[file_id] = file
    state_store.upsert_item("eeg_files", file)
    return {"id": file_id, "label": label, "status": "updated"}


def delete_eeg_file(file_id: str) -> None:
    get_eeg_file(file_id)
    _eeg_files.pop(file_id, None)
    state_store.delete_item("eeg_files", file_id)
