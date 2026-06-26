import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import accounts, admin, artifacts, billing, data_crud, data_preparation, eeg_files, epilepsy_workbench, health, lab_demo, projects, reports, subjects, tasks, templates, workflow

app = FastAPI(
    title="QuanLan Analyser API",
    version="0.1.0",
    description="Research EEG analysis platform API for the V1 formal architecture.",
)

DEFAULT_CORS_ORIGINS = [
    "http://127.0.0.1:4174",
    "http://localhost:4174",
    "http://localhost:4177",
    "http://127.0.0.1:4177",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://127.0.0.1:8765",
    "http://localhost:8765",
    "http://39.97.248.225",
]


def _cors_origins() -> list[str]:
    configured = os.getenv("QLANALYSER_CORS_ORIGINS", "").strip()
    if not configured:
        return DEFAULT_CORS_ORIGINS
    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    return origins or DEFAULT_CORS_ORIGINS


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(accounts.router, prefix="/api", tags=["accounts"])
app.include_router(lab_demo.router, prefix="/api", tags=["lab-demo"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(subjects.router, prefix="/api", tags=["subjects"])
app.include_router(eeg_files.router, prefix="/api", tags=["eeg-files"])
app.include_router(templates.router, prefix="/api", tags=["templates"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(artifacts.router, prefix="/api", tags=["artifacts"])
app.include_router(epilepsy_workbench.router, prefix="/api", tags=["epilepsy-workbench"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(billing.router, prefix="/api", tags=["billing"])
app.include_router(data_crud.router, prefix="/api", tags=["data-crud"])
app.include_router(data_preparation.router, prefix="/api", tags=["data-preparation"])
app.include_router(workflow.router, prefix="/api", tags=["workflow"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
