import os
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import accounts, admin, artifacts, billing, data_crud, data_preparation, eeg_files, epilepsy_workbench, health, lab_demo, lab_edf_reviewer, lab_epilepsy_full_flow, projects, reports, subjects, tasks, teaching_data, templates, workflow
from backend.services import account_service

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

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
    "http://localhost:4176",
    "http://127.0.0.1:4176",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://127.0.0.1:8765",
    "http://localhost:8765",
    "http://39.97.248.225",
    "http://127.0.0.1:8001",
    "http://localhost:8001",
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

# 公开端点：无需认证
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(accounts.router, prefix="/api", tags=["accounts"])
app.include_router(lab_demo.router, prefix="/api", tags=["lab-demo"])
app.include_router(lab_edf_reviewer.router, prefix="/api", tags=["lab-edf-reviewer"])
app.include_router(lab_epilepsy_full_flow.router, prefix="/api", tags=["lab-epilepsy-full-flow"])
app.include_router(teaching_data.router, prefix="/api", tags=["teaching-data"])

# 需认证端点
app.include_router(projects.router, prefix="/api", tags=["projects"], dependencies=[Depends(account_service.require_current_account)])
app.include_router(subjects.router, prefix="/api", tags=["subjects"], dependencies=[Depends(account_service.require_current_account)])
app.include_router(eeg_files.router, prefix="/api", tags=["eeg-files"], dependencies=[Depends(account_service.require_current_account)])
app.include_router(templates.router, prefix="/api", tags=["templates"], dependencies=[Depends(account_service.require_current_account)])
app.include_router(tasks.router, prefix="/api", tags=["tasks"], dependencies=[Depends(account_service.require_current_account)])
app.include_router(artifacts.router, prefix="/api", tags=["artifacts"], dependencies=[Depends(account_service.require_current_account)])
app.include_router(epilepsy_workbench.router, prefix="/api", tags=["epilepsy-workbench"], dependencies=[Depends(account_service.require_current_account)])
app.include_router(reports.router, prefix="/api", tags=["reports"], dependencies=[Depends(account_service.require_current_account)])
app.include_router(billing.router, prefix="/api", tags=["billing"], dependencies=[Depends(account_service.require_current_account)])
app.include_router(data_crud.router, prefix="/api", tags=["data-crud"], dependencies=[Depends(account_service.require_current_account)])
app.include_router(data_preparation.router, prefix="/api", tags=["data-preparation"], dependencies=[Depends(account_service.require_current_account)])
app.include_router(workflow.router, prefix="/api", tags=["workflow"], dependencies=[Depends(account_service.require_current_account)])

# 需管理员权限
app.include_router(admin.router, prefix="/api", tags=["admin"], dependencies=[Depends(account_service.require_admin_account)])

# 静态文件（前端页面，放在 API 路由之后，避免拦截 API 请求）
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
