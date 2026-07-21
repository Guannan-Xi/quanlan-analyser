import os
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from backend.services import readiness_service

router = APIRouter()
STARTED_AT = time.time()
STARTED_AT_ISO = datetime.fromtimestamp(STARTED_AT, tz=timezone.utc).isoformat()


@router.get("/health")
def get_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "scope": "eeg-v01-production",
        "version": "0.1.0",
        "process_id": os.getpid(),
        "started_at": STARTED_AT_ISO,
        "uptime_sec": round(time.time() - STARTED_AT, 3),
    }


@router.get("/health/readiness")
def get_readiness() -> dict:
    return readiness_service.get_v01_readiness()
