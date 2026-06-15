from pathlib import Path

from fastapi import HTTPException, UploadFile

from backend.models.eeg_file import EEGFileRead
from backend.models.project import ProjectCreate, ProjectRead
from backend.models.subject import SubjectCreate, SubjectRead

ROOT = Path(__file__).resolve().parents[2]
UPLOAD_ROOT = ROOT / "data" / "uploads"

_projects: dict[str, ProjectRead] = {}
_subjects: dict[str, SubjectRead] = {}
_eeg_files: dict[str, EEGFileRead] = {}


def create_project(payload: ProjectCreate) -> ProjectRead:
    project = ProjectRead(**payload.model_dump())
    _projects[project.id] = project
    return project


def list_projects() -> list[ProjectRead]:
    return list(_projects.values())


def get_project(project_id: str) -> ProjectRead:
    try:
        return _projects[project_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


def create_subject(project_id: str, payload: SubjectCreate) -> SubjectRead:
    get_project(project_id)
    subject = SubjectRead(project_id=project_id, **payload.model_dump())
    _subjects[subject.id] = subject
    return subject


def list_subjects(project_id: str) -> list[SubjectRead]:
    get_project(project_id)
    return [subject for subject in _subjects.values() if subject.project_id == project_id]


async def create_eeg_file(project_id: str, subject_id: str | None, upload: UploadFile | None) -> EEGFileRead:
    get_project(project_id)
    if subject_id and subject_id not in _subjects:
        raise HTTPException(status_code=404, detail="Subject not found")

    filename = upload.filename if upload else "manual-placeholder.edf"
    suffix = Path(filename).suffix.lower().lstrip(".") or "unknown"
    project_dir = UPLOAD_ROOT / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    stored_path = project_dir / filename

    if upload:
        content = await upload.read()
        stored_path.write_bytes(content)
    elif not stored_path.exists():
        stored_path.write_text("placeholder for local development\n", encoding="utf-8")

    eeg_file = EEGFileRead(
        project_id=project_id,
        subject_id=subject_id,
        original_filename=filename,
        stored_path=stored_path,
        detected_format=suffix,
    )
    _eeg_files[eeg_file.id] = eeg_file
    return eeg_file


def get_eeg_file(file_id: str) -> EEGFileRead:
    try:
        return _eeg_files[file_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="EEG file not found") from exc
