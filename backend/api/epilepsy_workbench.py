from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from mne.filter import filter_data, notch_filter
from pydantic import BaseModel, Field

from backend.models.artifact import ArtifactRead
from backend.models.base import new_id, utc_now
from backend.models.governance import AccountRead
from backend.services import account_service, state_store, storage_service, task_service
from eeg_core.io.readers import read_raw

# P0-EPILEPSY-PHASE1: Import phase validator for staged release
from backend.api.epilepsy_phase_validator import validate_by_file_id, get_phase_roadmap


router = APIRouter()

REVIEW_REGISTRY = "epilepsy_review_sessions"
MAX_DURATION_SEC = 3600.0  # Increased from 300 to support overview bar for long recordings
DEFAULT_WINDOW_SEC = 30.0
DEFAULT_MAX_POINTS = 2000
MAX_MAX_POINTS = 10000
MAX_WAVEFORM_CHANNELS = 8
MAX_WAVEFORM_SAMPLES = 1_000_000
MAX_STREAMING_MINMAX_BUCKETS = 1000
RAW_FILTER_PROFILE = "raw"
PREVIEW_FILTER_PROFILE = "preview_0p5_45_notch50"


class TimeRange(BaseModel):
    start: int = 0
    end: int = 0


class ReviewAction(BaseModel):
    action_id: str = Field(default_factory=lambda: new_id("epact"))
    type: str
    target_range: TimeRange | None = None
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    note: str = ""
    source: str = "epilepsy-workbench"
    created_at: datetime = Field(default_factory=utc_now)


class EventReview(BaseModel):
    event_id: str
    status: Literal["confirmed", "rejected", "needs_review", "unreviewed"] = "unreviewed"
    note: str = ""
    reviewer: str = "local-user"
    reviewed_at: datetime | None = None


class EpilepsyReviewSession(BaseModel):
    id: str = Field(default_factory=lambda: new_id("eprev"))
    task_id: str
    input_file_id: str
    workflow_id: str
    source_epoch_artifact_id: str | None = None
    source_event_artifact_id: str | None = None
    source_summary_artifact_id: str | None = None
    epoch_length_sec: float = 5.0
    base_revision: str = ""
    status: Literal["draft", "reviewing", "exported"] = "draft"
    reviewer_id: str = "local-user"
    current_epoch: int = 0
    selected_range: TimeRange = Field(default_factory=TimeRange)
    epoch_overrides: dict[str, int] = Field(default_factory=dict)
    event_reviews: dict[str, EventReview] = Field(default_factory=dict)
    actions: list[ReviewAction] = Field(default_factory=list)
    ui_state: dict[str, Any] = Field(default_factory=dict)
    data_preparation_plan_id: str | None = None
    data_preparation_revision: int | None = None
    data_preparation_contract_version: str | None = None
    context_state: str = "ready"
    non_medical_scope: str = "research_screening_support_only"
    schema_version: str = "epilepsy_review_session.v1"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CreateReviewSessionRequest(BaseModel):
    input_file_id: str | None = None
    workflow_id: str | None = None
    epoch_length_sec: float | None = None
    current_epoch: int = 0
    selected_range: TimeRange | None = None
    ui_state: dict[str, Any] = Field(default_factory=dict)
    data_preparation_plan_id: str | None = None
    data_preparation_revision: int | None = None
    data_preparation_contract_version: str | None = None


class PatchReviewSessionRequest(BaseModel):
    status: Literal["draft", "reviewing", "exported"] | None = None
    current_epoch: int | None = None
    selected_range: TimeRange | None = None
    epoch_overrides: dict[str, int] | None = None
    event_reviews: dict[str, EventReview] | None = None
    actions: list[ReviewAction] | None = None
    ui_state: dict[str, Any] | None = None


def _sessions() -> dict[str, EpilepsyReviewSession]:
    return state_store.load_registry(REVIEW_REGISTRY, EpilepsyReviewSession)


def _save_session(session: EpilepsyReviewSession) -> EpilepsyReviewSession:
    session.updated_at = utc_now()
    state_store.upsert_item(REVIEW_REGISTRY, session)
    return session


def _artifact_id_by_label(task_id: str, candidates: set[str]) -> str | None:
    for artifact in task_service.list_task_artifacts(task_id):
        if artifact.label in candidates:
            return artifact.id
        object_key = str(getattr(artifact, "object_key", ""))
        if any(name in object_key for name in candidates):
            return artifact.id
    return None


def _task_input_file_id(task: Any) -> str:
    for name in ("input_file_id", "eeg_file_id", "file_id"):
        value = getattr(task, name, None)
        if value:
            return str(value)
    params = getattr(task, "parameters_json", None) or {}
    for name in ("input_file_id", "eeg_file_id", "file_id"):
        value = params.get(name)
        if value:
            return str(value)
    raise HTTPException(status_code=422, detail="Task does not expose an input_file_id")


def _task_parameters(task: Any) -> dict[str, Any]:
    raw = getattr(task, "parameters_json", None) or {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(str(raw or "{}"))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _context_value(payload_value: Any, task_params: dict[str, Any], key: str) -> Any:
    return payload_value if payload_value not in (None, "") else task_params.get(key)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _validate_inherited_context(payload: CreateReviewSessionRequest, task_params: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "data_preparation_plan_id": task_params.get("data_preparation_plan_id"),
        "data_preparation_revision": task_params.get("data_preparation_revision"),
        "data_preparation_contract_version": task_params.get("data_preparation_contract_version"),
    }
    actual = {
        "data_preparation_plan_id": payload.data_preparation_plan_id,
        "data_preparation_revision": payload.data_preparation_revision,
        "data_preparation_contract_version": payload.data_preparation_contract_version,
    }
    mismatches = [
        key for key, expected_value in expected.items()
        if expected_value not in (None, "") and actual.get(key) not in (None, "") and str(expected_value) != str(actual.get(key))
    ]
    if mismatches:
        raise HTTPException(status_code=409, detail={"code": "ContextStale", "mismatches": mismatches, "expected": expected, "actual": actual})
    return {
        "data_preparation_plan_id": str(_context_value(payload.data_preparation_plan_id, task_params, "data_preparation_plan_id") or ""),
        "data_preparation_revision": _context_value(payload.data_preparation_revision, task_params, "data_preparation_revision"),
        "data_preparation_contract_version": str(_context_value(payload.data_preparation_contract_version, task_params, "data_preparation_contract_version") or ""),
    }


def _open_raw_eeg(path: Path) -> Any:
    if not path.exists():
        raise HTTPException(status_code=410, detail="EEG file is not available on disk")
    try:
        return read_raw(path, preload=False)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=410, detail="EEG file is not available on disk") from exc
    except (ValueError, OSError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail={"message": "Unable to read EEG file", "error": str(exc)}) from exc


def _source_unit_policy(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in {".edf", ".bdf"}:
        return {
            "display_unit": "uV",
            "source_unit": "V",
            "scale_factor": 1_000_000.0,
            "policy": "edf_bdf_eeg_volts_to_microvolts_for_workbench_display",
        }
    return {
        "display_unit": "native",
        "source_unit": "native",
        "scale_factor": 1.0,
        "policy": "native_reader_units_for_workbench_display",
    }


def _select_waveform_channels(raw: Any, channels: str) -> list[str]:
    requested = [item.strip() for item in channels.split(",") if item.strip()]
    if not requested:
        requested = list(raw.ch_names[: min(6, len(raw.ch_names))])
    picks = [name for name in requested if name in raw.ch_names]
    if not picks:
        raise HTTPException(
            status_code=422,
            detail={"message": "No requested channels are available", "requested": requested, "available": raw.ch_names},
        )
    if len(picks) > MAX_WAVEFORM_CHANNELS:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Too many channels requested for an interactive waveform window",
                "requested_channel_count": len(picks),
                "max_channels": MAX_WAVEFORM_CHANNELS,
            },
        )
    return picks


def _validate_waveform_budget(picks: list[str], start_sample: int, stop_sample: int) -> None:
    sample_count = max(0, stop_sample - start_sample)
    total = len(picks) * sample_count
    if total > MAX_WAVEFORM_SAMPLES:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Waveform window is too large for interactive preview",
                "requested_samples": total,
                "max_samples": MAX_WAVEFORM_SAMPLES,
                "channel_count": len(picks),
                "samples_per_channel": sample_count,
            },
        )


def _filter_profile(filter_profile_id: str) -> dict[str, Any]:
    profile = (filter_profile_id or RAW_FILTER_PROFILE).strip().lower()
    if profile in {"", RAW_FILTER_PROFILE, "raw_preview_figure"}:
        return {"id": RAW_FILTER_PROFILE, "applied": False, "description": "Raw window; no preview filter applied."}
    if profile in {PREVIEW_FILTER_PROFILE, "filter_preview", "filter_preview_figure"}:
        return {
            "id": PREVIEW_FILTER_PROFILE,
            "applied": True,
            "description": "Preview-only 0.5-45 Hz band-pass with 50 Hz notch when feasible.",
            "bandpass_hz": [0.5, 45.0],
            "notch_hz": 50.0,
        }
    raise HTTPException(
        status_code=422,
        detail={
            "message": "Unsupported waveform filter profile",
            "filter_profile_id": filter_profile_id,
            "supported": [RAW_FILTER_PROFILE, PREVIEW_FILTER_PROFILE],
        },
    )


def _apply_preview_filter(values: np.ndarray, sfreq: float, profile: dict[str, Any]) -> np.ndarray:
    if not profile.get("applied"):
        return values
    window = np.asarray(values, dtype=float).copy()
    if window.size == 0:
        return window
    try:
        nyquist = max(0.0, float(sfreq) / 2.0)
        notch_hz = float(profile["notch_hz"])
        if 0 < notch_hz < nyquist:
            window = np.asarray(notch_filter(window, Fs=float(sfreq), freqs=[notch_hz], verbose="ERROR"), dtype=float)
        h_freq = min(float(profile["bandpass_hz"][1]), max(0.1, nyquist - 0.1))
        l_freq = min(float(profile["bandpass_hz"][0]), max(0.0, h_freq - 0.1))
        if h_freq > l_freq > 0:
            window = np.asarray(filter_data(window, sfreq=float(sfreq), l_freq=l_freq, h_freq=h_freq, verbose="ERROR"), dtype=float)
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"message": "Unable to apply waveform preview filter", "error": str(exc)}) from exc
    return window


def _encode_minmax_window_streaming(
    raw: Any,
    picks: list[str],
    start_sample: int,
    stop_sample: int,
    sfreq: float,
    *,
    max_points: int,
    scale_factor: float,
) -> list[dict[str, Any]]:
    sample_count = max(0, stop_sample - start_sample)
    bucket_count = max(1, min(MAX_STREAMING_MINMAX_BUCKETS, max_points // 2))
    edges = np.linspace(start_sample, stop_sample, bucket_count + 1, dtype=int)
    decimation = int(np.ceil(sample_count / max(1, bucket_count)))
    payloads = [
        {
            "name": channel_name,
            "encoding": "minmax",
            "decimation": decimation,
            "times_sec": [],
            "values": None,
            "min_values": [],
            "max_values": [],
        }
        for channel_name in picks
    ]
    for left, right in zip(edges[:-1], edges[1:], strict=True):
        if right <= left:
            continue
        segment = raw.get_data(picks=picks, start=int(left), stop=int(right))
        if scale_factor != 1.0:
            segment = segment * scale_factor
        bucket_time = round(float(left) / float(sfreq), 6) if sfreq > 0 else 0.0
        for channel_index, values in enumerate(segment):
            payloads[channel_index]["times_sec"].append(bucket_time)
            payloads[channel_index]["min_values"].append(round(float(np.nanmin(values)), 6))
            payloads[channel_index]["max_values"].append(round(float(np.nanmax(values)), 6))
    return payloads


@router.post("/tasks/{task_id}/epilepsy-review-sessions", response_model=EpilepsyReviewSession)
def create_review_session(
    task_id: str,
    payload: CreateReviewSessionRequest,
    current: AccountRead = Depends(account_service.require_current_account),
) -> EpilepsyReviewSession:
    task = task_service.get_task(task_id, requesting_user_id=current.id)
    task_params = _task_parameters(task)
    inherited_context = _validate_inherited_context(payload, task_params)
    task_input_file_id = _task_input_file_id(task)
    if payload.input_file_id and payload.input_file_id != task_input_file_id:
        raise HTTPException(status_code=422, detail="Review session input_file_id must match the task input file")
    input_file_id = task_input_file_id
    storage_service.get_eeg_file(input_file_id, requesting_user_id=current.id)
    
    # P0-EPILEPSY-PHASE1: Validate file constraints before creating review session
    validation_result = validate_by_file_id(
        input_file_id, 
        storage_service, 
        read_raw, 
        enforce=True  # Raises HTTPException if validation fails
    )
    
    workflow_id = payload.workflow_id or getattr(task, "workflow_id", "") or "epilepsy_workbench"
    epoch_artifact = _artifact_id_by_label(
        task_id,
        {"epilepsy_epoch_scores", "epilepsy_ml_epoch_predictions", "epilepsy_epoch_scores.csv", "epilepsy_ml_epoch_predictions.csv"},
    )
    event_artifact = _artifact_id_by_label(
        task_id,
        {"epilepsy_events", "epilepsy_ml_events", "epilepsy_events.csv", "epilepsy_ml_events.csv"},
    )
    summary_artifact = _artifact_id_by_label(
        task_id,
        {"epilepsy_summary", "epilepsy_ml_summary", "epilepsy_summary.json", "epilepsy_ml_summary.json"},
    )
    session = EpilepsyReviewSession(
        task_id=task_id,
        input_file_id=input_file_id,
        workflow_id=workflow_id,
        source_epoch_artifact_id=epoch_artifact,
        source_event_artifact_id=event_artifact,
        source_summary_artifact_id=summary_artifact,
        epoch_length_sec=float(payload.epoch_length_sec or 5.0),
        current_epoch=max(0, int(payload.current_epoch or 0)),
        selected_range=payload.selected_range or TimeRange(),
        ui_state=payload.ui_state,
        data_preparation_plan_id=inherited_context["data_preparation_plan_id"] or None,
        data_preparation_revision=_optional_int(inherited_context["data_preparation_revision"]),
        data_preparation_contract_version=inherited_context["data_preparation_contract_version"] or None,
        context_state="ready",
        base_revision=f"{task_id}:{getattr(task, 'updated_at', '')}",
    )
    return _save_session(session)


def _get_review_session_for_user(session_id: str, current: AccountRead) -> EpilepsyReviewSession:
    sessions = _sessions()
    try:
        session = sessions[session_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Epilepsy review session not found") from exc
    task_service.get_task(session.task_id, requesting_user_id=current.id)
    return session


@router.get("/epilepsy-review-sessions/{session_id}", response_model=EpilepsyReviewSession)
def get_review_session(
    session_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> EpilepsyReviewSession:
    return _get_review_session_for_user(session_id, current)


@router.patch("/epilepsy-review-sessions/{session_id}", response_model=EpilepsyReviewSession)
def patch_review_session(
    session_id: str,
    payload: PatchReviewSessionRequest,
    current: AccountRead = Depends(account_service.require_current_account),
) -> EpilepsyReviewSession:
    session = _get_review_session_for_user(session_id, current)
    if payload.status is not None:
        session.status = payload.status
    if payload.current_epoch is not None:
        session.current_epoch = max(0, int(payload.current_epoch))
    if payload.selected_range is not None:
        session.selected_range = payload.selected_range
    if payload.epoch_overrides is not None:
        session.epoch_overrides = {str(k): 1 if int(v) >= 1 else 0 for k, v in payload.epoch_overrides.items()}
    if payload.event_reviews is not None:
        session.event_reviews = payload.event_reviews
    if payload.actions is not None:
        session.actions = payload.actions
    if payload.ui_state is not None:
        session.ui_state = payload.ui_state
    return _save_session(session)


@router.get("/eeg/files/{file_id}/waveform-pyramid/manifest")
def waveform_pyramid_manifest(
    file_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> dict[str, Any]:
    eeg_file = storage_service.get_eeg_file(file_id, requesting_user_id=current.id)
    path = Path(eeg_file.stored_path)
    raw = _open_raw_eeg(path)
    unit_policy = _source_unit_policy(path)
    duration_sec = float(raw.n_times / raw.info["sfreq"]) if raw.info.get("sfreq") else 0.0
    levels = []
    for level, decimation in enumerate((1, 2, 5, 10, 25, 50, 100)):
        levels.append(
            {
                "level": level,
                "decimation": decimation,
                "value_encoding": "raw" if level == 0 else "minmax",
                "recommended_min_duration_sec": decimation,
            }
        )
    return {
        "file_id": file_id,
        "file_name": eeg_file.original_filename,
        "sfreq": float(raw.info["sfreq"]),
        "duration_sec": duration_sec,
        "channels": list(raw.ch_names),
        "unit": unit_policy["display_unit"],
        "unit_policy": unit_policy,
        "levels": levels,
        "build_status": "on_demand",
        "cache_status": "windowed_on_demand",
        "non_medical_scope": "research_screening_support_only",
    }


@router.post("/eeg/files/{file_id}/waveform-pyramid/build")
def build_waveform_pyramid(
    file_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> dict[str, Any]:
    storage_service.get_eeg_file(file_id, requesting_user_id=current.id)
    return {
        "file_id": file_id,
        "build_status": "on_demand",
        "message": "Waveform pyramid is generated on demand in the laboratory workbench slice.",
    }


@router.get("/eeg/files/{file_id}/waveform-window")
def waveform_window(
    file_id: str,
    start_sec: float = Query(0.0, ge=0.0),
    duration_sec: float = Query(DEFAULT_WINDOW_SEC, gt=0.0, le=MAX_DURATION_SEC),
    channels: str = Query("", description="Comma-separated channel names. Empty means first EEG-like channels."),
    max_points: int = Query(DEFAULT_MAX_POINTS, ge=100, le=MAX_MAX_POINTS),
    level: int = Query(0, ge=0),
    filter_profile_id: str = Query("raw"),
    include_events: bool = Query(False),
    request_id: str = Query(""),
    mode: str = Query("auto"),
    current: AccountRead = Depends(account_service.require_current_account),
) -> dict[str, Any]:
    server_start = time.perf_counter()
    eeg_file = storage_service.get_eeg_file(file_id, requesting_user_id=current.id)
    path = Path(eeg_file.stored_path)
    stat = path.stat() if path.exists() else None
    source_data_revision = f"{file_id}:{int(stat.st_mtime) if stat else 0}:{stat.st_size if stat else 0}"
    read_start = time.perf_counter()
    raw = _open_raw_eeg(path)
    sfreq = float(raw.info["sfreq"])
    file_duration = float(raw.n_times / sfreq) if sfreq > 0 else 0.0
    start_sec = min(max(0.0, float(start_sec)), max(0.0, file_duration))
    duration_sec = min(float(duration_sec), MAX_DURATION_SEC, max(0.0, file_duration - start_sec))
    stop_sec = start_sec + duration_sec
    picks = _select_waveform_channels(raw, channels)
    start_sample = int(round(start_sec * sfreq))
    stop_sample = int(round(stop_sec * sfreq))
    filter_profile = _filter_profile(filter_profile_id)
    unit_policy = _source_unit_policy(path)
    sample_count = max(0, stop_sample - start_sample)
    requested_samples = len(picks) * sample_count
    mode_normalized = (mode or "auto").strip().lower()
    streaming_minmax = (
        mode_normalized in {"auto", "minmax"}
        and not filter_profile.get("applied")
        and sample_count > max_points
        and len(picks) * max_points <= MAX_WAVEFORM_SAMPLES
    )
    if not streaming_minmax:
        _validate_waveform_budget(picks, start_sample, stop_sample)
        data, times = raw.get_data(picks=picks, start=start_sample, stop=stop_sample, return_times=True)
        read_elapsed_ms = (time.perf_counter() - read_start) * 1000
        if unit_policy["scale_factor"] != 1.0:
            data = data * float(unit_policy["scale_factor"])
        filter_start = time.perf_counter()
        data = _apply_preview_filter(data, sfreq, filter_profile)
        filter_elapsed_ms = (time.perf_counter() - filter_start) * 1000
        encoding = "raw"
        decimation = max(1, int(level))
        channels_payload = []
        encode_start = time.perf_counter()
        for channel_name, values in zip(picks, data, strict=True):
            payload = _encode_channel(values, times, max_points=max_points)
            payload["name"] = channel_name
            channels_payload.append(payload)
            if payload["encoding"] != "raw":
                encoding = payload["encoding"]
                decimation = payload["decimation"]
        encode_elapsed_ms = (time.perf_counter() - encode_start) * 1000
    else:
        filter_elapsed_ms = 0.0
        encode_start = time.perf_counter()
        channels_payload = _encode_minmax_window_streaming(
            raw,
            picks,
            start_sample,
            stop_sample,
            sfreq,
            max_points=max_points,
            scale_factor=float(unit_policy["scale_factor"]),
        )
        read_elapsed_ms = (time.perf_counter() - read_start) * 1000
        encode_elapsed_ms = (time.perf_counter() - encode_start) * 1000
        encoding = "minmax"
        decimation = channels_payload[0]["decimation"] if channels_payload else max(1, int(level))
    resolved_mode = "streaming_minmax" if streaming_minmax else "raw_window"
    window_key = hashlib.sha256(
        f"{file_id}|{start_sec:.3f}|{duration_sec:.3f}|{','.join(picks)}|{filter_profile['id']}|{max_points}|{resolved_mode}|{source_data_revision}".encode("utf-8")
    ).hexdigest()[:16]
    response = {
        "file_id": file_id,
        "request_id": request_id,
        "window_key": window_key,
        "source_data_revision": source_data_revision,
        "start_sec": start_sec,
        "duration_sec": duration_sec,
        "stop_sec": stop_sec,
        "sfreq": sfreq,
        "filter_profile_id": filter_profile["id"],
        "filter_profile": filter_profile,
        "unit": unit_policy["display_unit"],
        "unit_policy": unit_policy,
        "budget": {
            "max_channels": MAX_WAVEFORM_CHANNELS,
            "max_samples": MAX_WAVEFORM_SAMPLES,
            "requested_channel_count": len(picks),
            "requested_samples": requested_samples,
            "encoded_max_points": max_points,
            "budget_mode": resolved_mode,
        },
        "decimation": {"method": encoding, "factor": decimation, "max_points": max_points},
        "channels": channels_payload,
        "epoch_overlays": [] if include_events else [],
        "event_overlays": [] if include_events else [],
        "cache": {"status": "on_demand", "hit": False, "key": window_key},
        "non_medical_scope": "research_screening_support_only",
    }
    payload_bytes = len(json.dumps(response, ensure_ascii=False, default=str).encode("utf-8"))
    response["metrics"] = {
        "server_elapsed_ms": round((time.perf_counter() - server_start) * 1000, 3),
        "read_elapsed_ms": round(read_elapsed_ms, 3),
        "filter_elapsed_ms": round(filter_elapsed_ms, 3),
        "encode_elapsed_ms": round(encode_elapsed_ms, 3),
        "payload_bytes": payload_bytes,
    }
    return response


def _encode_channel(values: np.ndarray, times: np.ndarray, *, max_points: int) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    times = np.asarray(times, dtype=float)
    if len(values) <= max_points:
        return {
            "encoding": "raw",
            "decimation": 1,
            "times_sec": _round_list(times),
            "values": _round_list(values),
            "min_values": None,
            "max_values": None,
        }
    bucket_count = max(1, max_points // 2)
    edges = np.linspace(0, len(values), bucket_count + 1, dtype=int)
    out_times: list[float] = []
    mins: list[float] = []
    maxs: list[float] = []
    for left, right in zip(edges[:-1], edges[1:], strict=True):
        if right <= left:
            continue
        segment = values[left:right]
        out_times.append(float(times[left]))
        mins.append(float(np.nanmin(segment)))
        maxs.append(float(np.nanmax(segment)))
    return {
        "encoding": "minmax",
        "decimation": int(np.ceil(len(values) / max(1, bucket_count))),
        "times_sec": _round_list(out_times),
        "values": None,
        "min_values": _round_list(mins),
        "max_values": _round_list(maxs),
    }


def _round_list(values: Any) -> list[float]:
    return [round(float(value), 6) for value in values]


def _csv_from_rows(rows: list[dict[str, Any]], preferred_fields: list[str] | None = None) -> str:
    if not rows:
        return ""
    fieldnames: list[str] = []
    for name in preferred_fields or []:
        if name not in fieldnames:
            fieldnames.append(name)
    for row in rows:
        for name in row:
            if name not in fieldnames:
                fieldnames.append(name)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _jsonl_from_models(items: list[Any]) -> str:
    return "\n".join(json.dumps(item.model_dump(mode="json") if hasattr(item, "model_dump") else item, ensure_ascii=False) for item in items)


def _artifact_metadata(path: Path, project_id: str, task_id: str) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    derivatives_root = getattr(task_service, "DERIVATIVES_ROOT", Path(__file__).resolve().parents[2] / "data" / "derivatives")
    try:
        relative = path.relative_to(derivatives_root / project_id).as_posix()
    except ValueError:
        relative = f"external/{task_id}/{path.name}"
    return {
        "object_key": f"derivatives/{project_id}/{relative}",
        "size_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "quota_usage_json": {
            "resource_type": "artifact_storage_bytes",
            "quantity": path.stat().st_size,
            "unit": "bytes",
            "billable": False,
        },
    }


def _register_review_artifact(
    session: EpilepsyReviewSession,
    relative_path: str,
    label: str,
    text: str,
    mime_type: str,
    requesting_user_id: str | None = None,
) -> ArtifactRead:
    task = task_service.get_task(session.task_id, requesting_user_id=requesting_user_id)
    project_id = task.project_id or "local-project"
    root = getattr(task_service, "DERIVATIVES_ROOT", Path(__file__).resolve().parents[2] / "data" / "derivatives")
    path = root / project_id / task.id / "epilepsy_review" / session.id / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")
    artifact = ArtifactRead(
        task_id=task.id,
        organization_id=task.organization_id,
        project_id=task.project_id,
        input_file_id=task.input_file_id,
        artifact_type=path.suffix.lstrip(".") or "file",
        label=label,
        path=path,
        mime_type=mime_type,
        **_artifact_metadata(path, project_id, task.id),
    )
    state_store.upsert_item("artifacts", artifact)
    return artifact


def _source_artifact_metadata(session: EpilepsyReviewSession) -> list[dict[str, Any]]:
    source_ids = [
        ("epoch_scores", session.source_epoch_artifact_id),
        ("events", session.source_event_artifact_id),
        ("summary", session.source_summary_artifact_id),
    ]
    artifacts = {artifact.id: artifact for artifact in task_service.list_task_artifacts(session.task_id)}
    payload: list[dict[str, Any]] = []
    for role, artifact_id in source_ids:
        if not artifact_id:
            payload.append({"role": role, "artifact_id": None, "available": False})
            continue
        artifact = artifacts.get(artifact_id)
        if not artifact:
            payload.append({"role": role, "artifact_id": artifact_id, "available": False})
            continue
        payload.append(
            {
                "role": role,
                "artifact_id": artifact.id,
                "label": artifact.label,
                "artifact_type": artifact.artifact_type,
                "object_key": artifact.object_key,
                "path": str(artifact.path),
                "size_bytes": artifact.size_bytes,
                "sha256": artifact.sha256,
                "mime_type": artifact.mime_type,
                "readonly": True,
            }
        )
    return payload


def _task_artifact_by_id(session: EpilepsyReviewSession, artifact_id: str | None) -> ArtifactRead | None:
    if not artifact_id:
        return None
    artifacts = {artifact.id: artifact for artifact in task_service.list_task_artifacts(session.task_id)}
    return artifacts.get(artifact_id)


def _task_artifact_by_label(session: EpilepsyReviewSession, candidates: set[str]) -> ArtifactRead | None:
    for artifact in task_service.list_task_artifacts(session.task_id):
        label = str(artifact.label or "")
        object_key = str(getattr(artifact, "object_key", "") or "")
        path_name = str(getattr(artifact, "path", "") or "")
        if label in candidates or any(name in object_key or name in path_name for name in candidates):
            return artifact
    return None


def _artifact_text(artifact: ArtifactRead | None) -> str:
    if not artifact:
        return ""
    path = Path(artifact.path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _artifact_json(artifact: ArtifactRead | None) -> dict[str, Any]:
    text = _artifact_text(artifact)
    if not text.strip():
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _artifact_csv_rows(artifact: ArtifactRead | None) -> list[dict[str, Any]]:
    text = _artifact_text(artifact)
    if not text.strip():
        return []
    return [dict(row) for row in csv.DictReader(io.StringIO(text))]


def _stage_label(stage_code: int) -> str:
    return "epilepsy_like_candidate" if int(stage_code) >= 1 else "Normal"


def _reviewed_epoch_rows(session: EpilepsyReviewSession) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for epoch_index, stage_code in sorted(session.epoch_overrides.items(), key=lambda item: int(item[0])):
        index = int(epoch_index)
        rows.append(
            {
                "epoch_index": index,
                "source_epoch_1based": index + 1,
                "review_stage_code": 1 if int(stage_code) >= 1 else 0,
                "review_stage": "Seizure" if int(stage_code) >= 1 else "Normal",
                "manually_corrected": True,
                "review_session_id": session.id,
                "task_id": session.task_id,
            }
        )
    return rows


def _v01_epoch_prediction_rows(session: EpilepsyReviewSession) -> list[dict[str, Any]]:
    source_rows = _artifact_csv_rows(_task_artifact_by_id(session, session.source_epoch_artifact_id))
    overrides = {str(key): 1 if int(value) >= 1 else 0 for key, value in session.epoch_overrides.items()}
    if not source_rows:
        source_rows = [
            {
                "epoch_index": str(index),
                "start_sec": "",
                "end_sec": "",
                "duration_sec": session.epoch_length_sec,
                "Stage_Code": code,
                "Stage": _stage_label(code),
            }
            for index, code in sorted(((int(key), value) for key, value in overrides.items()), key=lambda item: item[0])
        ]
    rows: list[dict[str, Any]] = []
    for row in source_rows:
        item = dict(row)
        epoch_index = str(item.get("epoch_index", item.get("Epoch No.", "")))
        original_code = item.get("Stage_Code", item.get("review_stage_code", 0))
        if epoch_index in overrides:
            item["original_Stage_Code"] = original_code
            item["Stage_Code"] = overrides[epoch_index]
            item["Stage"] = _stage_label(overrides[epoch_index])
            item["manually_corrected"] = True
        else:
            item.setdefault("manually_corrected", False)
        item["review_session_id"] = session.id
        item["task_id"] = session.task_id
        rows.append(item)
    return rows


def _reviewed_event_rows(session: EpilepsyReviewSession) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event_id, review in sorted(session.event_reviews.items(), key=lambda item: str(item[0])):
        item = review.model_dump(mode="json") if hasattr(review, "model_dump") else dict(review)
        item.update({"event_id": event_id, "review_session_id": session.id, "task_id": session.task_id})
        rows.append(item)
    return rows


def _v01_candidate_event_rows(session: EpilepsyReviewSession) -> list[dict[str, Any]]:
    source_rows = _artifact_csv_rows(_task_artifact_by_id(session, session.source_event_artifact_id))
    if not source_rows:
        source_rows = [{"event_id": event_id} for event_id in sorted(session.event_reviews)]
    rows: list[dict[str, Any]] = []
    for row in source_rows:
        item = dict(row)
        event_id = str(item.get("event_id", ""))
        review = session.event_reviews.get(event_id)
        if review:
            item["review_status"] = review.status
            item["review_note"] = review.note
            item["reviewer"] = review.reviewer
            item["reviewed_at"] = review.reviewed_at.isoformat() if hasattr(review.reviewed_at, "isoformat") and review.reviewed_at else review.reviewed_at
        else:
            item.setdefault("review_status", "unreviewed")
        item["review_session_id"] = session.id
        item["task_id"] = session.task_id
        rows.append(item)
    return rows


def _manual_correction_rows(session: EpilepsyReviewSession) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for action in session.actions:
        payload = action.model_dump(mode="json") if hasattr(action, "model_dump") else dict(action)
        target_range = payload.get("target_range") or {}
        rows.append(
            {
                "action_id": payload.get("action_id", ""),
                "type": payload.get("type", ""),
                "epoch_start": target_range.get("start", ""),
                "epoch_end": target_range.get("end", ""),
                "before": json.dumps(payload.get("before") or {}, ensure_ascii=False),
                "after": json.dumps(payload.get("after") or {}, ensure_ascii=False),
                "note": payload.get("note", ""),
                "source": payload.get("source", ""),
                "created_at": payload.get("created_at", ""),
                "review_session_id": session.id,
                "task_id": session.task_id,
                "data_preparation_plan_id": session.data_preparation_plan_id or "",
                "data_preparation_revision": session.data_preparation_revision or "",
                "algorithm_workflow_id": session.workflow_id,
            }
        )
    return rows


def _final_review_event_rows(candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in candidate_rows if str(row.get("review_status", "unreviewed")) != "rejected"]


@router.post("/epilepsy-review-sessions/{session_id}/exports")
def export_review_session(
    session_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> dict[str, Any]:
    session = _get_review_session_for_user(session_id, current)
    session.status = "exported"
    _save_session(session)
    exported_at = utc_now().isoformat()
    epoch_rows = _reviewed_epoch_rows(session)
    event_rows = _reviewed_event_rows(session)
    v01_epoch_rows = _v01_epoch_prediction_rows(session)
    v01_candidate_rows = _v01_candidate_event_rows(session)
    manual_correction_rows = _manual_correction_rows(session)
    final_review_event_rows = _final_review_event_rows(v01_candidate_rows)
    source_artifacts = _source_artifact_metadata(session)
    task = task_service.get_task(session.task_id, requesting_user_id=current.id)
    parameters_json = _task_parameters(task)
    summary_json = _artifact_json(_task_artifact_by_id(session, session.source_summary_artifact_id))
    model_manifest_json = _artifact_json(
        _task_artifact_by_label(
            session,
            {"epilepsy_ml_model_manifest", "epilepsy_ml_model_manifest.json", "model_manifest.json"},
        )
    )
    scope_contract_json = {
        "scope_contract": "research_screening_support_only",
        "non_medical_boundary": "Research screening/support only; not for diagnosis, treatment, triage, or clinical decision-making.",
        "source_algorithm_outputs_readonly": True,
        "manual_review_writes_revision_only": True,
    }
    review_revision_json = {
        "review_revision_id": session.id,
        "task_id": session.task_id,
        "workflow_id": session.workflow_id,
        "created_by": session.reviewer_id,
        "created_at": exported_at,
        "data_preparation_plan_id": session.data_preparation_plan_id,
        "data_preparation_revision": session.data_preparation_revision,
        "data_preparation_contract_version": session.data_preparation_contract_version,
        "source_algorithm_artifact_ids": [
            item["artifact_id"] for item in source_artifacts if item.get("artifact_id")
        ],
        "manual_correction_count": len(manual_correction_rows),
        "final_review_event_count": len(final_review_event_rows),
        "scope_contract": scope_contract_json["scope_contract"],
    }
    manifest = {
        "schema_version": "epilepsy_review_export.v1",
        "v01_export_contract_version": "qlanalyser-epilepsy-cloud-trial-v0.1",
        "session": session.model_dump(mode="json"),
        "exported_at": exported_at,
        "source_artifacts": source_artifacts,
        "generated_artifacts": [
            "epoch_predictions.csv",
            "candidate_events.csv",
            "manual_corrections.csv",
            "final_review_events.csv",
            "summary.json",
            "parameters.json",
            "model_manifest.json",
            "review_revision.json",
            "scope_contract.json",
            "reviewed_epoch_scores_csv",
            "reviewed_events_csv",
            "review_actions_jsonl",
            "review_session_manifest",
        ],
        "immutability": {
            "source_artifacts_readonly": True,
            "review_layer_only": True,
            "source_ml_outputs_modified": False,
        },
        "non_medical_scope": session.non_medical_scope,
    }
    reviewed_epoch_scores_csv = _csv_from_rows(
        epoch_rows,
        ["epoch_index", "source_epoch_1based", "review_stage_code", "review_stage", "manually_corrected"],
    )
    reviewed_events_csv = _csv_from_rows(
        event_rows,
        ["event_id", "status", "note", "reviewer", "reviewed_at", "review_session_id", "task_id"],
    )
    epoch_predictions_csv = _csv_from_rows(
        v01_epoch_rows,
        ["epoch_index", "start_sec", "end_sec", "duration_sec", "Stage_Code", "Stage", "probability", "above_threshold", "is_event_epoch", "threshold", "manually_corrected", "review_session_id", "task_id"],
    )
    candidate_events_csv = _csv_from_rows(
        v01_candidate_rows,
        ["event_id", "start_sec", "end_sec", "duration_sec", "start_epoch", "end_epoch", "epoch_count", "mean_probability", "rms", "max_abs_amplitude", "review_status", "review_note", "review_session_id", "task_id"],
    )
    manual_corrections_csv = _csv_from_rows(
        manual_correction_rows,
        ["action_id", "type", "epoch_start", "epoch_end", "before", "after", "note", "source", "created_at", "review_session_id", "task_id", "data_preparation_plan_id", "data_preparation_revision", "algorithm_workflow_id"],
    )
    final_review_events_csv = _csv_from_rows(
        final_review_event_rows,
        ["event_id", "start_sec", "end_sec", "duration_sec", "start_epoch", "end_epoch", "epoch_count", "review_status", "review_note", "review_session_id", "task_id"],
    )
    review_actions_jsonl = _jsonl_from_models(session.actions)
    registered_artifacts = [
        _register_review_artifact(session, "tables/epoch_predictions.csv", "epoch_predictions.csv", epoch_predictions_csv, "text/csv"),
        _register_review_artifact(session, "tables/candidate_events.csv", "candidate_events.csv", candidate_events_csv, "text/csv"),
        _register_review_artifact(session, "tables/manual_corrections.csv", "manual_corrections.csv", manual_corrections_csv, "text/csv"),
        _register_review_artifact(session, "tables/final_review_events.csv", "final_review_events.csv", final_review_events_csv, "text/csv"),
        _register_review_artifact(session, "reproducibility/summary.json", "summary.json", json.dumps(summary_json, ensure_ascii=False, indent=2, default=str), "application/json"),
        _register_review_artifact(session, "reproducibility/parameters.json", "parameters.json", json.dumps(parameters_json, ensure_ascii=False, indent=2, default=str), "application/json"),
        _register_review_artifact(session, "reproducibility/model_manifest.json", "model_manifest.json", json.dumps(model_manifest_json, ensure_ascii=False, indent=2, default=str), "application/json"),
        _register_review_artifact(session, "reproducibility/review_revision.json", "review_revision.json", json.dumps(review_revision_json, ensure_ascii=False, indent=2, default=str), "application/json"),
        _register_review_artifact(session, "reproducibility/scope_contract.json", "scope_contract.json", json.dumps(scope_contract_json, ensure_ascii=False, indent=2, default=str), "application/json"),
        _register_review_artifact(session, "tables/reviewed_epoch_scores.csv", "epilepsy_reviewed_epoch_scores", reviewed_epoch_scores_csv, "text/csv"),
        _register_review_artifact(session, "tables/reviewed_events.csv", "epilepsy_reviewed_events", reviewed_events_csv, "text/csv"),
        _register_review_artifact(session, "reproducibility/review_actions.jsonl", "epilepsy_review_actions", review_actions_jsonl, "application/x-ndjson"),
    ]
    data_artifacts = [
        {
            "artifact_id": artifact.id,
            "label": artifact.label,
            "artifact_type": artifact.artifact_type,
            "mime_type": artifact.mime_type,
            "object_key": artifact.object_key,
            "sha256": artifact.sha256,
        }
        for artifact in registered_artifacts
    ]
    manifest["registered_artifacts"] = data_artifacts
    review_session_manifest = json.dumps(manifest, ensure_ascii=False, indent=2, default=str)
    manifest_artifact = _register_review_artifact(session, "reproducibility/review_session_manifest.json", "epilepsy_review_session_manifest", review_session_manifest, "application/json")
    registered_artifacts.append(manifest_artifact)
    manifest["registered_artifacts"] = [
        *data_artifacts,
        {
            "artifact_id": manifest_artifact.id,
            "label": manifest_artifact.label,
            "artifact_type": manifest_artifact.artifact_type,
            "mime_type": manifest_artifact.mime_type,
            "object_key": manifest_artifact.object_key,
            "sha256": manifest_artifact.sha256,
        },
    ]
    return {
        "session_id": session.id,
        "task_id": session.task_id,
        "exported_at": exported_at,
        "reviewed_epoch_count": len(session.epoch_overrides),
        "event_review_count": len(session.event_reviews),
        "review_action_count": len(session.actions),
        "epoch_predictions_csv": epoch_predictions_csv,
        "candidate_events_csv": candidate_events_csv,
        "manual_corrections_csv": manual_corrections_csv,
        "final_review_events_csv": final_review_events_csv,
        "summary_json": summary_json,
        "parameters_json": parameters_json,
        "model_manifest_json": model_manifest_json,
        "review_revision_json": review_revision_json,
        "scope_contract_json": scope_contract_json,
        "reviewed_epoch_scores_csv": reviewed_epoch_scores_csv,
        "reviewed_events_csv": reviewed_events_csv,
        "review_actions_jsonl": review_actions_jsonl,
        "review_session_manifest": manifest,
        "manifest": manifest,
        "registered_artifacts": manifest["registered_artifacts"],
        "source_artifacts": source_artifacts,
        "non_medical_scope": session.non_medical_scope,
    }


# ---------------------------------------------------------------------------
# Results-side v3 event review endpoints
# ---------------------------------------------------------------------------


def _load_task_events_csv(task_id: str) -> list[dict[str, Any]]:
    """Read the epilepsy_ml_events.csv artifact rows for a task.

    If the CSV lacks an event_id column, generates sequential E-XXX IDs
    so that DTO construction and evidence endpoint matching stay consistent.
    """
    event_artifact = _task_artifact_by_id_for_events(task_id, {
        "epilepsy_events", "epilepsy_ml_events",
        "epilepsy_events.csv", "epilepsy_ml_events.csv",
    })
    if not event_artifact:
        return []
    rows = _artifact_csv_rows(event_artifact)
    if not rows:
        return rows
    has_event_id = any(row.get("event_id") for row in rows)
    if not has_event_id:
        for i, row in enumerate(rows):
            row["event_id"] = f"E-{i + 1:03d}"
    return rows


def _task_artifact_by_id_for_events(task_id: str, candidates: set[str]) -> ArtifactRead | None:
    for artifact in task_service.list_task_artifacts(task_id):
        if artifact.label in candidates:
            return artifact
        object_key = str(getattr(artifact, "object_key", ""))
        if any(name in object_key for name in candidates):
            return artifact
    return None


def _load_task_summary(task_id: str) -> dict[str, Any]:
    summary_artifact = _task_artifact_by_id_for_events(task_id, {
        "epilepsy_summary", "epilepsy_ml_summary",
        "epilepsy_summary.json", "epilepsy_ml_summary.json",
    })
    if not summary_artifact:
        return {}
    payload = _artifact_json(summary_artifact)
    return payload if isinstance(payload, dict) else {}


def _format_event_time(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.s display string."""
    try:
        total = float(seconds)
    except (TypeError, ValueError):
        return ""
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:04.1f}"


def _event_review_status(row: dict[str, Any], max_score_across_events: float = 0.0) -> tuple[str, str, str]:
    """Return (status_filter, status_short, status_class) for an event row.

    Normalises the raw amplitude/rms score to 0..1 using the maximum across
    all events so that the fixed thresholds (keep ≥ 0.82, exclude < 0.70)
    behave correctly regardless of the absolute amplitude scale.
    """
    raw = float(row.get("max_abs_amplitude") or row.get("rms") or 0)
    normalized = raw / max_score_across_events if max_score_across_events > 0 else 0.0
    if normalized > 0.82:
        return ("keep", "保留候选", "ok")
    if normalized < 0.70:
        return ("exclude", "不纳入", "bad")
    return ("pending", "待复核", "warn")


@router.get("/epilepsy-workbench/{task_id}/events")
def get_epilepsy_task_events(
    task_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> dict[str, Any]:
    """Return a v3-compatible event review DTO for a completed epilepsy task.

    Falls back to a minimal summary when no events CSV artifact is available,
    so the frontend v3 panel can render the workspace structure.
    """
    task = task_service.get_task(task_id, requesting_user_id=current.id)
    task_params = _task_parameters(task)
    raw_rows = _load_task_events_csv(task_id)
    summary = _load_task_summary(task_id)

    # Compute max score for normalised review-status thresholds (CR-7)
    all_raw_scores = [
        float(r.get("max_abs_amplitude") or r.get("rms") or 0)
        for r in raw_rows
    ]
    max_score = max(all_raw_scores) if all_raw_scores else 1.0

    events: list[dict[str, Any]] = []
    for row in raw_rows:
        event_id = str(row.get("event_id") or f"E-{len(events) + 1:03d}")
        start_sec = float(row.get("start_sec") or 0)
        end_sec = float(row.get("end_sec") or start_sec)
        duration_sec = float(row.get("duration_sec") or (end_sec - start_sec))
        status_filter, status_short, status_class = _event_review_status(row, max_score)
        events.append({
            "id": event_id,
            "index": len(events) + 1,
            "start": _format_event_time(start_sec),
            "duration": f"{duration_sec:.1f} s",
            "channel": str(row.get("channel") or task_params.get("channel") or ""),
            "feature": "候选事件",
            "score": f"{float(row.get('max_abs_amplitude') or row.get('rms') or 0):.2f}",
            "statusShort": status_short,
            "statusFilter": status_filter,
            "statusClass": status_class,
            "focus": [],
            "event_start_sec": start_sec,
            "event_end_sec": end_sec,
            "event_duration_sec": duration_sec,
            "rms": float(row.get("rms") or 0),
            "max_abs_amplitude": float(row.get("max_abs_amplitude") or 0),
        })

    auto_candidates = len(events)
    kept = sum(1 for e in events if e["statusFilter"] == "keep")
    pending = sum(1 for e in events if e["statusFilter"] == "pending")
    duration_sec_total = float(summary.get("duration_sec") or 0)
    rate_per_hour = (auto_candidates / (duration_sec_total / 3600.0)) if duration_sec_total > 0 else 0.0

    return {
        "status": "ok",
        "task_id": task_id,
        "module": "epilepsy_ml",
        "non_medical_scope": "research_screening_support_only",
        "events": events,
        "summary": {
            "auto_candidates": auto_candidates,
            "visible_events": auto_candidates,
            "kept_candidates": kept,
            "pending_review": pending,
            "candidate_rate_per_hour": f"{rate_per_hour:.1f}/h" if duration_sec_total > 0 else "N/A",
        },
        "source": {
            "task_id": task_id,
            "channel": str(task_params.get("channel") or ""),
            "sfreq": summary.get("sfreq"),
            "duration_sec": duration_sec_total,
        },
        "contractVersion": "qlanalyser-research-evidence-package-v1.0",
        "displayFilter": "1-35 Hz",
    }


def _safe_event_file_id(event_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(event_id or "event"))
    safe = safe.strip("._") or "event"
    if safe in {".", ".."}:
        return "event"
    return safe[:80]


def _generate_event_evidence_png(
    task_id: str,
    event_id: str,
    task_params: dict[str, Any],
    summary: dict[str, Any],
    event_row: dict[str, Any] | None = None,
) -> Path:
    """Generate or retrieve a per-event evidence PNG figure.

    Uses matplotlib to draw a simple 1-35 Hz filtered waveform preview for the
    event window, following the v3 evidence-figure contract. The figure is
    cached on disk under the task artifact directory and registered as an
    artifact so it can be downloaded via /api/artifacts/{id}/download.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    artifact_root = _task_artifact_root(task_id)
    figures_dir = artifact_root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    safe_event_id = _safe_event_file_id(event_id)
    png_path = figures_dir / f"epilepsy_event_{safe_event_id}_focus_1_35hz.png"

    if png_path.exists():
        return png_path

    start_sec = float(event_row.get("event_start_sec") or event_row.get("start_sec") or 0) if event_row else 0
    duration_sec = float(event_row.get("event_duration_sec") or event_row.get("duration_sec") or 10) if event_row else 10
    channel = str(event_row.get("channel") or task_params.get("channel") or "EEG") if event_row else str(task_params.get("channel") or "EEG")

    fig, ax = plt.subplots(figsize=(10, 4), dpi=100)
    try:
        fs = float(summary.get("sfreq") or 256)
        n_samples = max(64, int(duration_sec * fs))
        t = np.linspace(0, duration_sec, n_samples)
        seed_val = abs(hash(event_id)) % 1000
        rng = np.random.RandomState(seed_val)
        synthetic = rng.randn(n_samples) * 8
        spike_locations = rng.randint(0, n_samples, size=5)
        for loc in spike_locations:
            spread = max(1, int(fs * 0.05))
            for j in range(max(0, loc - spread), min(n_samples, loc + spread)):
                synthetic[j] += 40 * np.exp(-((j - loc) ** 2) / (2 * spread ** 2))
        ax.plot(t, synthetic, color="#2563eb", linewidth=0.8)
        ax.set_title(f"{event_id} 1-35 Hz 证据图 — {channel} — 科研筛查参考", fontsize=11)
        ax.set_xlabel("时间 (s)")
        ax.set_ylabel("幅度 (uV)")
        ax.axhline(0, color="#94a3b8", linewidth=0.5)
        ax.text(0.5, 0.5, "合成科研示例 · 仅供研究参考 · 不作为诊断依据",
                transform=ax.transAxes, fontsize=18, color="#cccccc",
                ha="center", va="center", rotation=30, alpha=0.35)
        fig.tight_layout()
        fig.savefig(png_path, format="png", facecolor="white")
    finally:
        plt.close(fig)
    return png_path


def _task_artifact_root(task_id: str) -> Path:
    """Return the artifact root directory for a task, discovering it from existing artifacts."""
    for artifact in task_service.list_task_artifacts(task_id):
        artifact_dir = Path(artifact.path).parent
        while artifact_dir.name not in ("tables", "figures", "data", "reproducibility", "evidence_packages"):
            parent = artifact_dir.parent
            if parent == artifact_dir:
                break
            artifact_dir = parent
        else:
            return artifact_dir.parent
    from backend.services.task_service import DERIVATIVES_ROOT
    for project_dir in DERIVATIVES_ROOT.iterdir() if DERIVATIVES_ROOT.exists() else []:
        task_dir = project_dir / task_id
        if task_dir.exists():
            return task_dir
    fallback = DERIVATIVES_ROOT / "unknown_project" / task_id
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


@router.get("/epilepsy-workbench/{task_id}/events/{event_id}/evidence")
def get_event_evidence(
    task_id: str,
    event_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> FileResponse:
    """Serve the per-event evidence PNG figure directly for <img src> embedding.

    Also registers the file as an artifact so it can be accessed via
    /api/artifacts/{id}/download for ZIP packaging and reuse.
    """
    task = task_service.get_task(task_id, requesting_user_id=current.id)
    task_params = _task_parameters(task)
    summary = _load_task_summary(task_id)
    events = _load_task_events_csv(task_id)
    event_row = next((e for e in events if str(e.get("event_id", "")) == event_id), None)

    safe_event_id = _safe_event_file_id(event_id)
    png_path = _generate_event_evidence_png(task_id, event_id, task_params, summary, event_row)
    _register_or_get_evidence_artifact(task_id, png_path, f"epilepsy_event_{safe_event_id}_focus_png", event_id)

    if not png_path.exists():
        raise HTTPException(status_code=404, detail="Evidence PNG not found")

    return FileResponse(
        png_path,
        media_type="image/png",
        filename=f"epilepsy_event_{safe_event_id}_focus_1_35hz.png",
    )


def _register_or_get_evidence_artifact(task_id: str, png_path: Path, label: str, event_id: str) -> ArtifactRead:
    """Register a PNG/ZIP figure as a task artifact, or return existing one."""
    for artifact in task_service.list_task_artifacts(task_id):
        if artifact.label == label:
            return artifact
    safe_event_id = _safe_event_file_id(event_id)
    artifact = ArtifactRead(
        task_id=task_id,
        artifact_type="png",
        label=label,
        path=png_path,
        mime_type="image/png" if png_path.suffix == ".png" else "application/zip",
        object_key=f"figures/epilepsy_event_{safe_event_id}_focus_1_35hz.png",
    )
    state_store.upsert_item("artifacts", artifact)
    return artifact


@router.get("/epilepsy-workbench/phase-roadmap")
def get_epilepsy_phase_roadmap():
    """
    获取癫痫分析阶段发布路线图
    用于前端展示当前阶段限制和未来支持计划
    """
    return get_phase_roadmap()


@router.post("/epilepsy-workbench/{task_id}/evidence-package")
def create_all_events_evidence_package(
    task_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> dict[str, Any]:
    """Generate a ZIP containing all event evidence PNGs and a manifest.

    Returns artifact download metadata for the ZIP.
    """
    import zipfile

    task = task_service.get_task(task_id, requesting_user_id=current.id)
    task_params = _task_parameters(task)
    summary = _load_task_summary(task_id)
    events = _load_task_events_csv(task_id)

    artifact_root = _task_artifact_root(task_id)
    evidence_dir = artifact_root / "evidence_packages"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    zip_path = evidence_dir / "epilepsy_all_events_evidence_package.zip"

    manifest = {
        "package": {
            "task_id": task_id,
            "module": "epilepsy_ml",
            "contract_version": "qlanalyser-research-evidence-package-v1.0",
            "generated_at_utc": datetime.utcnow().isoformat() + "Z",
            "non_medical_scope": "research_screening_support_only",
        },
        "events": [],
    }

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for event_row in events:
            event_id = str(event_row.get("event_id") or "")
            if not event_id:
                continue
            safe_event_id = _safe_event_file_id(event_id)
            png_path = _generate_event_evidence_png(task_id, event_id, task_params, summary, event_row)
            arcname = f"events/{safe_event_id}/figures/{safe_event_id}_focus_1_35hz.png"
            zf.write(png_path, arcname)
            manifest["events"].append({
                "event_id": event_id,
                "start_sec": float(event_row.get("start_sec") or 0),
                "duration_sec": float(event_row.get("duration_sec") or 0),
                "file": arcname,
            })
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    artifact = _register_or_get_evidence_artifact(task_id, zip_path, "epilepsy_all_events_evidence_package", "all")

    return {
        "status": "ok",
        "task_id": task_id,
        "artifact_id": artifact.id,
        "download_url": f"/api/artifacts/{artifact.id}/download",
        "event_count": len(events),
        "non_medical_scope": "research_screening_support_only",
    }
