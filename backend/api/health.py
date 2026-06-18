from fastapi import APIRouter

from backend.services import readiness_service

router = APIRouter()


@router.get("/health")
def get_health() -> dict[str, str]:
    return {"status": "ok", "scope": "eeg-v01-production", "version": "0.1.0"}


@router.get("/health/readiness")
def get_readiness() -> dict:
    return readiness_service.get_v01_readiness()
