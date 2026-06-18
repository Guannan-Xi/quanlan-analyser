from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import admin, artifacts, billing, data_crud, eeg_files, health, projects, reports, subjects, tasks, templates, workflow

app = FastAPI(
    title="QuanLan Analyser API",
    version="0.1.0",
    description="Research EEG analysis platform API for the V1 formal architecture.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:4174",
        "http://localhost:4174",
        "http://localhost:4177",
        "http://127.0.0.1:4177",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:8765",
        "http://localhost:8765",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(subjects.router, prefix="/api", tags=["subjects"])
app.include_router(eeg_files.router, prefix="/api", tags=["eeg-files"])
app.include_router(templates.router, prefix="/api", tags=["templates"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(artifacts.router, prefix="/api", tags=["artifacts"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(billing.router, prefix="/api", tags=["billing"])
app.include_router(data_crud.router, prefix="/api", tags=["data-crud"])
app.include_router(workflow.router, prefix="/api", tags=["workflow"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
