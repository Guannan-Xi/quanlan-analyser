"""
EDF Reviewer API Endpoints for QLanalyser Analysis Lab

Public lab-only endpoints for EDF waveform inspection and rendering.
No authentication required, no persistent storage.
"""

import json
import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from backend.services import lab_edf_reviewer_service


router = APIRouter()

# Max file size: 100MB (typical EDF limit)
MAX_FILE_SIZE = 100 * 1024 * 1024
_TRUE_ENV_VALUES = {"1", "true", "yes", "on", "y"}
_LOCAL_LAB_EDF_REVIEWER_ENVS = {"local", "dev", "development", "test", "ci", "sandbox"}


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUE_ENV_VALUES


def _public_lab_edf_reviewer_enabled() -> bool:
    if _env_flag("QLANALYSER_PUBLIC_LAB_EDF_REVIEWER_ENABLED"):
        return True
    if _env_flag("QLANALYSER_SANDBOX_MODE"):
        return True
    app_env = os.getenv("QLANALYSER_ENV", "").strip().lower()
    return app_env in _LOCAL_LAB_EDF_REVIEWER_ENVS


def _assert_public_lab_edf_reviewer_enabled() -> None:
    if not _public_lab_edf_reviewer_enabled():
        raise HTTPException(status_code=404, detail="Public EDF reviewer lab is disabled")


@router.post("/lab/edf-reviewer/inspect")
async def inspect_edf(file: UploadFile = File(...)) -> dict:
    """
    Inspect uploaded EDF metadata without loading full waveform.
    
    Lab-only endpoint: no persistence, no authentication required.
    
    Request:
        multipart/form-data with file field
        
    Response:
        {
          "sfreq": 250.0,
          "duration": 3600.0,
          "channels": ["EEG Fpz-Cz", "EEG Pz-Oz", ...],
          "meas_date": "2024-01-01T00:00:00",
          "channel_count": 8,
          "file_hash": "abc123..."
        }
        
    Raises:
        400: If file too large or EDF parsing fails
    """
    _assert_public_lab_edf_reviewer_enabled()
    if not file.filename or not file.filename.lower().endswith((".edf", ".fif", ".bdf")):
        raise HTTPException(400, "Only .edf / .fif / .bdf files are supported")
    
    raw_bytes = await file.read()
    
    if len(raw_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, f"EDF file too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")
    
    if len(raw_bytes) == 0:
        raise HTTPException(400, "Empty file uploaded")
    
    try:
        result = lab_edf_reviewer_service.inspect_edf_bytes(raw_bytes, filename=file.filename or "")
        return result
    except Exception as exc:
        raise HTTPException(400, "EDF parse failed") from exc


@router.post("/lab/edf-reviewer/waveform")
async def render_waveform(
    file: UploadFile = File(...),
    channels: str = Form(...),
    highpass: float = Form(1.0),
    lowpass: float = Form(35.0),
    notch: float = Form(50.0),
    max_points: int = Form(20000),
) -> dict:
    """
    Process EDF waveform for display: extract, filter, downsample, normalize.
    
    Lab-only endpoint: no persistence, no authentication required.
    
    Request:
        multipart/form-data with:
        - file: EDF file bytes
        - channels: JSON array of channel names, e.g. ["EEG Fpz-Cz", "ACC0"]
        - highpass: Highpass filter Hz (0 to disable), default 1.0
        - lowpass: Lowpass filter Hz (0 to disable), default 35.0
        - notch: Notch filter Hz (0/50/60), default 50.0
        - max_points: Max display points (downsampling), default 20000
        
    Response:
        {
          "times": [0.0, 0.004, ...],
          "values": [[0.123, ...], [0.987, ...]],  // normalized by base_scale
          "channels": ["EEG Fpz-Cz", "ACC0", "ACC RMS（体动）"],
          "base_scale": 45.2,
          "unit_label": "uV（按电压读数换算）",
          "sfreq": 250.0,
          "filter_summary": "高通 1 Hz；低通 35 Hz；陷波 50 Hz",
          "acc_rms_derived": true,
          "acc_rms_source_count": 2
        }
        
    Raises:
        400: If file too large, channel selection invalid, or processing fails
    """
    _assert_public_lab_edf_reviewer_enabled()
    if not file.filename or not file.filename.lower().endswith((".edf", ".fif", ".bdf")):
        raise HTTPException(400, "Only .edf / .fif / .bdf files are supported")
    
    raw_bytes = await file.read()
    
    if len(raw_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, f"EDF file too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")
    
    if len(raw_bytes) == 0:
        raise HTTPException(400, "Empty file uploaded")
    
    # Parse channel list
    try:
        channel_list = json.loads(channels)
        if not isinstance(channel_list, list) or not channel_list:
            raise ValueError("channels must be non-empty list")
    except Exception as exc:
        raise HTTPException(400, f"Invalid channels parameter: {str(exc)}") from exc
    
    # Validate filter parameters
    if highpass < 0 or lowpass < 0 or notch < 0:
        raise HTTPException(400, "Filter frequencies must be non-negative")
    
    if max_points < 100 or max_points > 100000:
        raise HTTPException(400, "max_points must be between 100 and 100000")
    
    try:
        result = lab_edf_reviewer_service.process_edf_waveform(
            raw_bytes=raw_bytes,
            channels=channel_list,
            highpass=float(highpass),
            lowpass=float(lowpass),
            notch=float(notch),
            max_points=int(max_points),
            filename=file.filename or "",
        )
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, "Waveform processing failed") from exc


@router.get("/lab/edf-reviewer/status")
def get_status() -> dict:
    """
    Health check for EDF Reviewer lab service.
    
    Returns:
        {"status": "ready", "service": "edf_reviewer_lab"}
    """
    _assert_public_lab_edf_reviewer_enabled()
    return {
        "status": "ready",
        "service": "edf_reviewer_lab",
        "max_file_size_mb": MAX_FILE_SIZE // 1024 // 1024,
    }
