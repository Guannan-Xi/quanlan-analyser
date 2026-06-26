from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from mne.filter import filter_data, notch_filter
from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now
from backend.services import state_store, storage_service, task_service
from eeg_core.io.readers import read_raw


router = APIRouter()

REVIEW_REGISTRY = "epilepsy_review_sessions"
MAX_DURATION_SEC = 300.0
DEFAULT_WINDOW_SEC = 30.0
DEFAULT_MAX_POINTS = 2000
MAX_MAX_POINTS = 10000
MAX_WAVEFORM_CHANNELS = 8
MAX_WAVEFORM_SAMPLES = 1_000_000
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


@router.post("/tasks/{task_id}/epilepsy-review-sessions", response_model=EpilepsyReviewSession)
def create_review_session(task_id: str, payload: CreateReviewSessionRequest) -> EpilepsyReviewSession:
    task = task_service.get_task(task_id)
    input_file_id = payload.input_file_id or _task_input_file_id(task)
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
        base_revision=f"{task_id}:{getattr(task, 'updated_at', '')}",
    )
    return _save_session(session)


@router.get("/epilepsy-review-sessions/{session_id}", response_model=EpilepsyReviewSession)
def get_review_session(session_id: str) -> EpilepsyReviewSession:
    sessions = _sessions()
    try:
        return sessions[session_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Epilepsy review session not found") from exc


@router.patch("/epilepsy-review-sessions/{session_id}", response_model=EpilepsyReviewSession)
def patch_review_session(session_id: str, payload: PatchReviewSessionRequest) -> EpilepsyReviewSession:
    session = get_review_session(session_id)
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
def waveform_pyramid_manifest(file_id: str) -> dict[str, Any]:
    eeg_file = storage_service.get_eeg_file(file_id)
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
def build_waveform_pyramid(file_id: str) -> dict[str, Any]:
    storage_service.get_eeg_file(file_id)
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
) -> dict[str, Any]:
    eeg_file = storage_service.get_eeg_file(file_id)
    path = Path(eeg_file.stored_path)
    raw = _open_raw_eeg(path)
    sfreq = float(raw.info["sfreq"])
    file_duration = float(raw.n_times / sfreq) if sfreq > 0 else 0.0
    start_sec = min(max(0.0, float(start_sec)), max(0.0, file_duration))
    duration_sec = min(float(duration_sec), MAX_DURATION_SEC, max(0.0, file_duration - start_sec))
    stop_sec = start_sec + duration_sec
    picks = _select_waveform_channels(raw, channels)
    start_sample = int(round(start_sec * sfreq))
    stop_sample = int(round(stop_sec * sfreq))
    _validate_waveform_budget(picks, start_sample, stop_sample)
    filter_profile = _filter_profile(filter_profile_id)
    unit_policy = _source_unit_policy(path)
    data, times = raw.get_data(picks=picks, start=start_sample, stop=stop_sample, return_times=True)
    if unit_policy["scale_factor"] != 1.0:
        data = data * float(unit_policy["scale_factor"])
    data = _apply_preview_filter(data, sfreq, filter_profile)
    encoding = "raw"
    decimation = max(1, int(level))
    channels_payload = []
    for channel_name, values in zip(picks, data, strict=True):
        payload = _encode_channel(values, times, max_points=max_points)
        payload["name"] = channel_name
        channels_payload.append(payload)
        if payload["encoding"] != "raw":
            encoding = payload["encoding"]
            decimation = payload["decimation"]
    return {
        "file_id": file_id,
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
            "requested_samples": len(picks) * max(0, stop_sample - start_sample),
        },
        "decimation": {"method": encoding, "factor": decimation, "max_points": max_points},
        "channels": channels_payload,
        "epoch_overlays": [] if include_events else [],
        "event_overlays": [] if include_events else [],
        "cache": {"status": "on_demand", "hit": False},
        "non_medical_scope": "research_screening_support_only",
    }


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


def _reviewed_event_rows(session: EpilepsyReviewSession) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event_id, review in sorted(session.event_reviews.items(), key=lambda item: str(item[0])):
        item = review.model_dump(mode="json") if hasattr(review, "model_dump") else dict(review)
        item.update({"event_id": event_id, "review_session_id": session.id, "task_id": session.task_id})
        rows.append(item)
    return rows


@router.post("/epilepsy-review-sessions/{session_id}/exports")
def export_review_session(session_id: str) -> dict[str, Any]:
    session = get_review_session(session_id)
    session.status = "exported"
    _save_session(session)
    exported_at = utc_now().isoformat()
    epoch_rows = _reviewed_epoch_rows(session)
    event_rows = _reviewed_event_rows(session)
    source_artifacts = _source_artifact_metadata(session)
    manifest = {
        "schema_version": "epilepsy_review_export.v1",
        "session": session.model_dump(mode="json"),
        "exported_at": exported_at,
        "source_artifacts": source_artifacts,
        "generated_artifacts": [
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
    return {
        "session_id": session.id,
        "task_id": session.task_id,
        "exported_at": exported_at,
        "reviewed_epoch_count": len(session.epoch_overrides),
        "event_review_count": len(session.event_reviews),
        "review_action_count": len(session.actions),
        "reviewed_epoch_scores_csv": _csv_from_rows(
            epoch_rows,
            ["epoch_index", "source_epoch_1based", "review_stage_code", "review_stage", "manually_corrected"],
        ),
        "reviewed_events_csv": _csv_from_rows(
            event_rows,
            ["event_id", "status", "note", "reviewer", "reviewed_at", "review_session_id", "task_id"],
        ),
        "review_actions_jsonl": _jsonl_from_models(session.actions),
        "review_session_manifest": manifest,
        "manifest": manifest,
        "source_artifacts": source_artifacts,
        "non_medical_scope": session.non_medical_scope,
    }
