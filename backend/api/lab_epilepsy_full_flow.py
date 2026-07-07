from __future__ import annotations

import csv
import io
import json
import math
import os
import re
from collections import OrderedDict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import numpy as np
from fastapi import APIRouter, Body, HTTPException, Query, Request

from eeg_core.io.readers import read_raw


router = APIRouter()

LAB_API_ENV = "QLANALYSER_LAB_EPILEPSY_FULL_FLOW_ENABLED"
APP_ENV = "QLANALYSER_ENV"
SAMPLE_ROOT_ENV = "QLANALYSER_LAB_HE_SAMPLE_ROOT"
SAFE_SAMPLE_ROOT = "work/sample_data/epilepsy/"
SUPPORTED_SUFFIXES = {".edf", ".bdf", ".fif", ".fiff"}
MAX_WAVEFORM_DURATION_SEC = 120.0
MAX_WAVEFORM_POINTS = 4000
MAX_SCAN_WINDOWS = 96
DEFAULT_SCAN_WINDOWS = 32
DEFAULT_SCAN_WINDOW_SEC = 4.0
DEFAULT_SCAN_TOP_K = 12
MAX_REVIEW_SESSIONS = 50
MAX_REVIEW_EVENTS = 200
MAX_REVIEW_ACTIONS = 300
MAX_REVIEW_PAYLOAD_CHARS = 200_000
MAX_TEXT_FIELD_CHARS = 2000
MAX_SAMPLE_RECORDS = 12
REVIEW_SESSION_STORE_DIR = Path(__file__).resolve().parents[2] / "work" / "lab_epilepsy_full_flow" / "review_sessions"
DEFAULT_CHANNELS = ["EEG1", "EEG2", "EMG", "ACC"]
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
LOCAL_APP_ENVS = {"local", "dev", "development", "test"}
LAB_SAMPLE_RECORD_ID_RE = re.compile(r"^he-\d{3,}$")
SENSITIVE_PAYLOAD_KEYS = {
    "source_path",
    "source_path_display",
    "local_source_path",
    "absolute_path",
    "root",
    "source_folder_display",
}
ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"(?i)\b[a-z]:[\\/][^\r\n\t\"<>|]+"),
    re.compile(r"\\\\[^\\/\s]+[\\/][^\r\n\t\"<>|]+"),
    re.compile(r"(?<![\w:])/(?:Users|home|mnt|var|tmp|opt|root|srv|data|Volumes)[^\r\n\t\"<>|]*"),
)


def _seed(event_id: str, start_sec: float, duration_sec: float, event_type: str, priority: str, channels: list[str]) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "start_sec": float(start_sec),
        "duration_sec": float(duration_sec),
        "end_sec": float(start_sec + duration_sec),
        "event_type": event_type,
        "priority": priority,
        "channels": channels,
    }


HE_CANDIDATE_SEEDS: dict[str, list[dict[str, Any]]] = {
    "he-105": [
        _seed("HE105-E001", 14 * 60 + 18.4, 1.7, "ied", "high", ["EEG1", "EEG2"]),
        _seed("HE105-E002", 4 * 3600 + 26 * 60 + 8.2, 12.6, "seizure_like", "high", ["EEG1", "EEG2"]),
        _seed("HE105-E003", 8 * 3600 + 6 * 60 + 12.0, 1.2, "ied", "medium", ["EEG1"]),
        _seed("HE105-E004", 17 * 3600 + 44 * 60 + 30.2, 7.8, "rhythmic", "medium", ["EEG2"]),
        _seed("HE105-E005", 28 * 3600 + 11 * 60 + 2.4, 0.9, "artifact_suspect", "low", ["EEG1", "EMG"]),
        _seed("HE105-E006", 41 * 3600 + 32 * 60 + 18.7, 2.1, "ied", "medium", ["EEG1", "EEG2"]),
        _seed("HE105-E007", 58 * 3600 + 5 * 60 + 44.0, 15.1, "seizure_like", "high", ["EEG2"]),
        _seed("HE105-E008", 67 * 3600 + 19 * 60 + 6.5, 1.5, "ied", "low", ["EEG1"]),
    ],
    "he-106": [
        _seed("HE106-E001", 1 * 3600 + 10 * 60 + 4.5, 6.9, "rhythmic", "high", ["EEG2"]),
        _seed("HE106-E002", 6 * 3600 + 49 * 60 + 2.0, 1.1, "ied", "medium", ["EEG1"]),
        _seed("HE106-E003", 13 * 3600 + 28 * 60 + 51.3, 2.4, "ied", "medium", ["EEG1", "EEG2"]),
        _seed("HE106-E004", 21 * 3600 + 9 * 60 + 13.1, 9.6, "seizure_like", "high", ["EEG1", "EEG2"]),
        _seed("HE106-E005", 35 * 3600 + 18 * 60 + 42.9, 1.0, "artifact_suspect", "low", ["EMG"]),
        _seed("HE106-E006", 49 * 3600 + 10 * 60 + 2.2, 2.2, "rhythmic", "low", ["EEG2"]),
        _seed("HE106-E007", 61 * 3600 + 52 * 60 + 24.4, 1.8, "ied", "medium", ["EEG1"]),
    ],
    "he-118": [
        _seed("HE118-E001", 38 * 60 + 14.1, 1.4, "ied", "medium", ["EEG1"]),
        _seed("HE118-E002", 3 * 3600 + 22 * 60 + 7.4, 11.4, "seizure_like", "high", ["EEG1", "EEG2"]),
        _seed("HE118-E003", 12 * 3600 + 8 * 60 + 37.5, 1.6, "ied", "high", ["EEG2"]),
        _seed("HE118-E004", 19 * 3600 + 47 * 60 + 54.0, 8.0, "rhythmic", "medium", ["EEG1", "EEG2"]),
        _seed("HE118-E005", 31 * 3600 + 40 * 60 + 9.6, 0.8, "artifact_suspect", "low", ["ACC"]),
        _seed("HE118-E006", 52 * 3600 + 2 * 60 + 30.2, 13.2, "seizure_like", "high", ["EEG2"]),
        _seed("HE118-E007", 64 * 3600 + 56 * 60 + 16.8, 1.3, "ied", "medium", ["EEG1"]),
    ],
}

LAB_REVIEW_SESSIONS: OrderedDict[str, dict[str, Any]] = OrderedDict()

EVENT_TYPE_EXPORT_LABELS = {
    "ied": "棘/尖波样候选（待复核）",
    "seizure_like": "节律性片段候选（待复核）",
    "rhythmic": "节律性片段候选（待复核）",
    "artifact_suspect": "伪迹候选",
    "candidate_window": "候选窗口",
}

STATUS_EXPORT_LABELS = {
    "confirmed": "纳入草稿候选",
    "rejected": "不纳入草稿",
    "needs_review": "存疑/需二次复核",
    "unreviewed": "未复核",
}

STATUS_ALIASES = {
    "kept": "confirmed",
    "included": "confirmed",
    "include": "confirmed",
    "excluded": "rejected",
    "exclude": "rejected",
    "uncertain": "needs_review",
    "pending": "needs_review",
}


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _host_without_port(value: str) -> str:
    text = (value or "").strip().lower()
    if not text:
        return ""
    parsed = urlsplit(text if "://" in text else f"//{text}")
    host = parsed.hostname or text
    return host.strip("[]")


def _is_local_host_value(value: str) -> bool:
    return _host_without_port(value) in LOCAL_HOSTS


def _comma_hosts_are_local(value: str) -> bool:
    if not value:
        return True
    return all(_is_local_host_value(part.strip()) for part in value.split(",") if part.strip())


def _origin_headers_are_local(request: Request) -> bool:
    for header in ("origin", "referer"):
        value = request.headers.get(header, "")
        if value and not _is_local_host_value(value):
            return False
    return True


def _forwarded_headers_are_local(request: Request) -> bool:
    forwarded = request.headers.get("forwarded", "")
    if forwarded:
        return False
    if not _comma_hosts_are_local(request.headers.get("x-forwarded-for", "")):
        return False
    if not _comma_hosts_are_local(request.headers.get("x-real-ip", "")):
        return False
    if not _comma_hosts_are_local(request.headers.get("x-forwarded-host", "")):
        return False
    return True


def _is_local_request(request: Request) -> bool:
    client_host = (request.client.host if request.client else "") or ""
    return (
        _is_local_host_value(client_host)
        and _is_local_host_value(request.headers.get("host", ""))
        and _origin_headers_are_local(request)
        and _forwarded_headers_are_local(request)
    )


def require_lab_local_request(request: Request) -> None:
    if not _env_flag(LAB_API_ENV):
        raise HTTPException(status_code=404, detail="Lab epilepsy full-flow API is disabled")
    if os.getenv(APP_ENV, "").strip().lower() not in LOCAL_APP_ENVS:
        raise HTTPException(status_code=404, detail="Lab epilepsy full-flow API requires explicit local development environment")
    if not _is_local_request(request):
        raise HTTPException(status_code=403, detail="Lab epilepsy full-flow API is local-only")


def _sample_root() -> Path:
    configured = os.getenv(SAMPLE_ROOT_ENV, "").strip()
    if not configured:
        raise HTTPException(status_code=503, detail=f"{SAMPLE_ROOT_ENV} is not configured")
    root = Path(configured).expanduser()
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=503, detail=f"{SAMPLE_ROOT_ENV} is not a readable directory")
    return root


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize_payload(item)
            for key, item in value.items()
            if str(key).lower() not in SENSITIVE_PAYLOAD_KEYS
        }
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, str):
        text = value[:MAX_TEXT_FIELD_CHARS]
        for pattern in ABSOLUTE_PATH_PATTERNS:
            text = pattern.sub("[local_path_redacted]", text)
        return text
    return value


def _require_object_list(value: Any, field_name: str, max_items: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise HTTPException(status_code=422, detail=f"{field_name} must be a list")
    if len(value) > max_items:
        raise HTTPException(status_code=413, detail=f"{field_name} exceeds {max_items} items")
    if not all(isinstance(item, dict) for item in value):
        raise HTTPException(status_code=422, detail=f"{field_name} items must be objects")
    return value


def _csv_text(rows: list[dict[str, Any]], headers: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in headers})
    return buffer.getvalue()


def _normalize_review_status(value: Any) -> str:
    text = str(value or "unreviewed").strip().lower()
    text = STATUS_ALIASES.get(text, text)
    if text in STATUS_EXPORT_LABELS:
        return text
    return "needs_review"


def _event_review_status(event: dict[str, Any]) -> str:
    return _normalize_review_status(event.get("status") or event.get("backend_status") or event.get("review_status"))


def _normalize_review_event(event: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(event)
    normalized["status"] = _event_review_status(normalized)
    return normalized


def _review_status_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"auto_candidates": len(events), "reviewed": 0, "confirmed": 0, "rejected": 0, "needs_review": 0, "unreviewed": 0}
    for event in events:
        status = _event_review_status(event)
        counts[status] += 1
        if status != "unreviewed":
            counts["reviewed"] += 1
    return counts


def _event_type_label(value: Any) -> str:
    text = str(value or "")
    return EVENT_TYPE_EXPORT_LABELS.get(text, text or "未标注候选类型")


def _review_status_label(value: Any) -> str:
    return STATUS_EXPORT_LABELS.get(_normalize_review_status(value), "存疑/需二次复核")


def _priority_label(value: Any) -> str:
    return {
        "high": "高",
        "medium": "中",
        "low": "低",
    }.get(str(value or "").lower(), str(value or "") or "未记录")


def _candidate_source_label(value: Any) -> str:
    text = str(value or "")
    if text == "bounded_full_record_window_scan_rms_ptp_v1":
        return "有限 EDF 窗口抽样后按波形幅度变化排序，供人工复核优先级使用"
    if text == "bounded_full_record_window_scan_metrics":
        return "有限 EDF 窗口抽样后的波形幅度变化指标"
    if text.startswith("fallback_seeded"):
        return "示例时间点回退包；仅用于流程预览，不能作为真实候选生成证据"
    if text:
        return text
    return "当前预览候选包"


def _review_session_path(session_id: str) -> Path:
    if not re.fullmatch(r"lab_ep_review_[a-f0-9]{12}", session_id or ""):
        raise HTTPException(status_code=404, detail="Lab review session not found")
    return REVIEW_SESSION_STORE_DIR / f"{session_id}.json"


def _safe_exception_summary(exc: Exception) -> str:
    message = str(_sanitize_payload(str(exc))).strip()
    if len(message) > 180:
        message = f"{message[:177]}..."
    return f"{type(exc).__name__}: {message or 'scan_failed'}"


def _persist_review_session(session: dict[str, Any]) -> None:
    session_id = str(session.get("session_id") or "")
    if not session_id:
        return
    REVIEW_SESSION_STORE_DIR.mkdir(parents=True, exist_ok=True)
    path = _review_session_path(session_id)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _load_review_session(session_id: str) -> dict[str, Any] | None:
    session = LAB_REVIEW_SESSIONS.get(session_id)
    if session:
        LAB_REVIEW_SESSIONS.move_to_end(session_id)
        return session
    path = _review_session_path(session_id)
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict) or loaded.get("session_id") != session_id:
        return None
    loaded["source"] = loaded.get("source") or "lab_epilepsy_full_flow_backend_file_sanitized"
    loaded["storage"] = loaded.get("storage") or "local_lab_json_file"
    LAB_REVIEW_SESSIONS[session_id] = loaded
    LAB_REVIEW_SESSIONS.move_to_end(session_id)
    while len(LAB_REVIEW_SESSIONS) > MAX_REVIEW_SESSIONS:
        LAB_REVIEW_SESSIONS.popitem(last=False)
    return loaded


def _customer_event_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for event in events:
        channels = event.get("channels", "")
        if isinstance(channels, list):
            channels = "|".join(str(item) for item in channels)
        rows.append({
            "事件编号": event.get("event_id", ""),
            "人工状态": _review_status_label(_event_review_status(event)),
            "候选类型": _event_type_label(event.get("event_type")),
            "起始秒": event.get("start_sec", ""),
            "结束秒": event.get("end_sec", ""),
            "时长秒": event.get("duration_sec", ""),
            "原始起始秒": event.get("original_start_sec", ""),
            "原始结束秒": event.get("original_end_sec", ""),
            "通道": channels,
            "展示证据等级": event.get("evidence_grade", ""),
            "复核优先级": _priority_label(event.get("priority")),
            "复核备注": event.get("review_note") or event.get("note") or "",
            "复核人": event.get("reviewer", ""),
            "复核时间": event.get("reviewed_at", ""),
            "候选来源": _candidate_source_label(event.get("event_source") or event.get("source", "")),
        })
    return rows


def _lab_review_export(session: dict[str, Any]) -> dict[str, Any]:
    events = list(session.get("reviewed_events") or [])
    actions = list(session.get("actions") or [])
    record = dict(session.get("record") or {})
    context = dict(session.get("context") or {})
    model = dict(session.get("model") or {})
    counts = _review_status_counts(events)
    state_marked_events = [event for event in events if _event_review_status(event) != "unreviewed"]
    confirmed_events = [event for event in events if _event_review_status(event) == "confirmed"]
    review_status = "partial_review_draft" if counts["needs_review"] + counts["unreviewed"] else "review_draft_ready"
    review_status_label = "部分人工状态标注（研究草稿）" if review_status == "partial_review_draft" else "当前候选包已完成人工状态标注（研究草稿）"
    event_headers = [
        "事件编号",
        "人工状态",
        "候选类型",
        "起始秒",
        "结束秒",
        "时长秒",
        "原始起始秒",
        "原始结束秒",
        "通道",
        "展示证据等级",
        "复核优先级",
        "复核备注",
        "复核人",
        "复核时间",
        "候选来源",
    ]
    event_rows = _customer_event_rows(events)
    action_rows = []
    for index, action in enumerate(actions, start=1):
        action_rows.append({
            "index": index,
            "action": action.get("action") or action.get("type") or "",
            "detail": action.get("detail") or action.get("note") or "",
            "created_at": action.get("at") or action.get("created_at") or "",
            "source": action.get("source") or "",
        })
    return {
        "schema_version": "qlanalyser.epilepsy.lab_review_export.v1",
        "session_id": session.get("session_id"),
        "saved_at": session.get("saved_at"),
        "non_medical_scope": "research_screening_support_only",
        "download_class": "复核草稿记录",
        "正式交付就绪": False,
        "reviewed_candidate_events_csv": _csv_text(event_rows, event_headers),
        "review_actions_csv": _csv_text(action_rows, ["index", "action", "detail", "created_at", "source"]),
        "reviewed_candidate_status_csv": _csv_text(_customer_event_rows(state_marked_events), event_headers),
        "draft_reportable_confirmed_candidates_csv": _csv_text(_customer_event_rows(confirmed_events), event_headers),
        "draft_included_events_csv": _csv_text(_customer_event_rows(state_marked_events), event_headers),
        "epoch_predictions_csv": _csv_text(event_rows, event_headers),
        "candidate_events_csv": _csv_text(event_rows, event_headers),
        "manual_corrections_csv": _csv_text(action_rows, ["index", "action", "detail", "created_at", "source"]),
        "candidate_review_state_csv": _csv_text(_customer_event_rows(state_marked_events), event_headers),
        "final_review_events_csv": _csv_text(_customer_event_rows(state_marked_events), event_headers),
        "summary_json": {
            **counts,
            "record_filename": record.get("filename"),
            "review_status": review_status,
            "review_status_label": review_status_label,
            "scope": "research_screening_support_only",
        },
        "parameters_json": {
            "workflow_id": context.get("workflow_id"),
            "候选来源记录": context.get("source_algorithm_artifact_id"),
            "detector_version": model.get("detector_version"),
            "threshold": model.get("threshold"),
        },
        "model_manifest_json": {
            "detector_version": model.get("detector_version") or "lab_preview_detector",
            "algorithm_status": "local_lab_preview_not_clinically_validated",
            "score_policy": "ranking_metric_not_probability",
        },
        "review_revision_json": {
            "session_id": session.get("session_id"),
            "saved_at": session.get("saved_at"),
            "review_session_schema_version": session.get("review_session_schema_version"),
            "source_artifacts_readonly": True,
            "review_layer_only": True,
        },
        "scope_contract_json": {
            "scope_contract": "research_screening_support_only",
            "clinical_use_allowed": False,
            "diagnosis_or_treatment_allowed": False,
            "notes": [
                "本数据包是本地科研筛查复核草稿。",
                "未复核或存疑候选不能写成结论。",
            ],
        },
    }


def _lab_review_report(session: dict[str, Any]) -> dict[str, Any]:
    export = _lab_review_export(session)
    summary = export["summary_json"]
    record = dict(session.get("record") or {})
    events = list(session.get("reviewed_events") or [])
    context = dict(session.get("context") or {})
    model = dict(session.get("model") or {})
    channels = record.get("channels") or []
    channels_text = "、".join(str(channel) for channel in channels) if isinstance(channels, list) else str(channels or "未记录")
    duration_hours = float(record.get("duration_sec") or 0) / 3600
    sfreq_text = f"{record.get('sfreq')} Hz" if record.get("sfreq") else "未记录"
    candidate_source = _candidate_source_label(context.get("source_algorithm_artifact_id") or model.get("detector_version") or "当前预览候选包")
    return {
        "schema_version": "qlanalyser.epilepsy.report_preview.v1",
        "source_review_schema_version": session.get("schema_version"),
        "non_medical_scope": "research_screening_support_only",
        "report_status": summary["review_status"],
        "report_status_label": summary["review_status_label"],
        "record": record,
        "summary": summary,
        "interpretation": (
            f"{record.get('filename', 'EEG 记录')} 当前预览候选包包含 {summary['auto_candidates']} 个候选片段；"
            f"其中 {summary['confirmed']} 个被纳入草稿候选，{summary['rejected']} 个暂不纳入草稿，"
            f"{summary['needs_review'] + summary['unreviewed']} 个仍为存疑或未复核。"
            "该分母仅代表当前已载入的预览候选包，不代表全记录完整检测器的事件负荷估计；这不是临床结论。"
        ),
        "methods": (
            f"输入记录为 {record.get('filename', 'EEG 记录')}，记录时长约 {duration_hours:.1f} 小时，"
            f"采样率 {sfreq_text}，通道为 {channels_text}。"
            f"候选来源为 {candidate_source}；当前本地预览读取有限真实 EDF 波形窗口，并保存候选复核层。"
            "复核状态映射为：纳入草稿候选、暂不纳入草稿、存疑/需二次复核、未复核。"
            "排序指标来自 RMS/PTP 预览值，不是概率、置信度、敏感性、特异性或诊断结论。"
            "正式报告仍需补齐滤波/参考设置、候选生成参数、真实证据图、复核人和可追溯清单。"
        ),
        "figure_manifest": [
            {
                "id": "eventTimeline",
                "title": "候选事件时间轴",
                "source": "manual_review_layer",
                "provenance": "local_lab_review_session",
            }
        ],
        "provenance": export["review_revision_json"],
        "confirmed_events": [event for event in events if _event_review_status(event) == "confirmed"],
        "all_reviewed_events": events,
        "actions": session.get("actions") or [],
    }


def _sanitized_record(record: dict[str, Any]) -> dict[str, Any]:
    cleaned = {
        key: _sanitize_payload(value)
        for key, value in record.items()
        if str(key).lower() not in SENSITIVE_PAYLOAD_KEYS
    }
    filename = Path(str(cleaned.get("filename") or "")).name
    if filename:
        cleaned["filename"] = filename
        cleaned["safe_source_path"] = f"{SAFE_SAMPLE_ROOT}{filename}"
    cleaned["path_visibility"] = "safe_relative"
    return cleaned


def _record_id_from_path(path: Path) -> str:
    return path.stem.lower().replace("_", "-")


def _sample_paths() -> list[Path]:
    root = _sample_root()
    paths: list[Path] = []
    for path in sorted(root.iterdir()):
        if len(paths) >= MAX_SAMPLE_RECORDS:
            break
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if not LAB_SAMPLE_RECORD_ID_RE.fullmatch(_record_id_from_path(path)):
            continue
        paths.append(path)
    return paths


def _sample_path(record_id: str) -> Path:
    for path in _sample_paths():
        if _record_id_from_path(path) == record_id:
            return path
    raise HTTPException(status_code=404, detail="HE sample record not found")


@lru_cache(maxsize=8)
def _metadata_for_path(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    raw = read_raw(path, preload=False)
    sfreq = float(raw.info["sfreq"])
    duration_sec = float(raw.n_times / sfreq) if sfreq > 0 else 0.0
    return {
        "sfreq": sfreq,
        "duration_sec": duration_sec,
        "channels": list(raw.ch_names),
        "channel_count": len(raw.ch_names),
        "n_times": int(raw.n_times),
        "meas_date": str(raw.info.get("meas_date")),
    }


def _record_payload(path: Path, request: Request, include_metadata: bool = False) -> dict[str, Any]:
    record_id = _record_id_from_path(path)
    safe_source_path = f"{SAFE_SAMPLE_ROOT}{path.name}"
    payload: dict[str, Any] = {
        "id": record_id,
        "file_id": f"he_sample_{record_id.replace('-', '_')}",
        "filename": path.name,
        "format": path.suffix.lower().lstrip("."),
        "size_bytes": path.stat().st_size,
        "source_path_display": safe_source_path,
        "safe_source_path": safe_source_path,
        "path_visibility": "safe_relative",
        "candidate_seed_count": len(HE_CANDIDATE_SEEDS.get(record_id, [])),
        "non_medical_scope": "research_screening_support_only",
    }
    if include_metadata:
        payload.update(_metadata_for_path(str(path)))
    return payload


def _pick_channels(raw_channels: list[str], requested: str = "") -> list[str]:
    exact = {name: name for name in raw_channels}
    upper_map = {name.upper(): name for name in raw_channels}
    if requested:
        picks = []
        for item in [part.strip() for part in requested.split(",") if part.strip()]:
            match = exact.get(item) or upper_map.get(item.upper())
            if match and match not in picks:
                picks.append(match)
        if picks:
            return picks[:8]
    selected = []
    for preferred in DEFAULT_CHANNELS:
        match = upper_map.get(preferred.upper())
        if match and match not in selected:
            selected.append(match)
    return (selected or raw_channels[:4])[:8]


def _scale_to_uv(data: np.ndarray) -> np.ndarray:
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return data
    robust = float(np.nanpercentile(np.abs(finite), 95))
    if robust < 1e-3:
        return data * 1_000_000.0
    return data


def _window_data(path: Path, start_sec: float, duration_sec: float, channels: str, max_points: int) -> dict[str, Any]:
    raw = read_raw(path, preload=False)
    sfreq = float(raw.info["sfreq"])
    duration_sec = min(max(float(duration_sec), 0.1), MAX_WAVEFORM_DURATION_SEC)
    start_sec = max(0.0, min(float(start_sec), max(0.0, float(raw.n_times / sfreq) - 0.1)))
    stop_sec = min(float(raw.n_times / sfreq), start_sec + duration_sec)
    start_sample = int(start_sec * sfreq)
    stop_sample = max(start_sample + 1, int(stop_sec * sfreq))
    picks = _pick_channels(list(raw.ch_names), channels)
    data = raw.get_data(picks=picks, start=start_sample, stop=stop_sample)
    data = _scale_to_uv(np.asarray(data, dtype=float))
    max_points = max(100, min(int(max_points), MAX_WAVEFORM_POINTS))
    sample_count = data.shape[1]
    step = max(1, int(math.ceil(sample_count / max_points)))
    data = data[:, ::step]
    times = (np.arange(data.shape[1]) * step + start_sample) / sfreq
    return {
        "record_id": _record_id_from_path(path),
        "filename": path.name,
        "start_sec": round(float(start_sec), 6),
        "duration_sec": round(float(stop_sec - start_sec), 6),
        "stop_sec": round(float(stop_sec), 6),
        "sfreq": sfreq,
        "decimation": step,
        "unit": "uV",
        "channels": [
            {
                "name": name,
                "times_sec": [round(float(value), 6) for value in times],
                "values": [round(float(value), 6) for value in row],
            }
            for name, row in zip(picks, data, strict=False)
        ],
        "source": "real_edf_window",
        "non_medical_scope": "research_screening_support_only",
    }


@lru_cache(maxsize=96)
def _cached_window_data(path_text: str, start_sec: float, duration_sec: float, channels: str, max_points: int) -> dict[str, Any]:
    return _window_data(
        Path(path_text),
        start_sec=start_sec,
        duration_sec=duration_sec,
        channels=channels,
        max_points=max_points,
    )


def _window_data_cached(path: Path, start_sec: float, duration_sec: float, channels: str, max_points: int) -> dict[str, Any]:
    return _cached_window_data(
        str(path),
        round(float(start_sec), 3),
        round(float(duration_sec), 3),
        channels,
        int(max_points),
    )


def _candidate_metrics(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    window = _window_data_cached(
        path,
        start_sec=max(0.0, float(event["start_sec"]) - 1.0),
        duration_sec=min(20.0, float(event["duration_sec"]) + 2.0),
        channels=",".join(event["channels"]),
        max_points=2000,
    )
    values = []
    for channel in window["channels"]:
        arr = np.asarray(channel["values"], dtype=float)
        if arr.size:
            values.append(arr)
    if not values:
        return {"rms_uv": 0.0, "ptp_uv": 0.0, "preview_rms_ptp_rank_score": 0.5}
    data = np.vstack(values)
    rms = float(np.sqrt(np.nanmean(np.square(data))))
    ptp = float(np.nanpercentile(data, 99) - np.nanpercentile(data, 1))
    score = max(0.05, min(0.99, 0.35 + np.log1p(max(rms, 0.0)) / 12.0 + np.log1p(max(ptp, 0.0)) / 18.0))
    return {
        "rms_uv": round(rms, 4),
        "ptp_uv": round(ptp, 4),
        "preview_rms_ptp_rank_score": round(score, 4),
    }


def _metric_score(rms_uv: float, ptp_uv: float) -> float:
    return round(max(0.05, min(0.99, 0.35 + np.log1p(max(rms_uv, 0.0)) / 12.0 + np.log1p(max(ptp_uv, 0.0)) / 18.0)), 4)


def _scan_candidate_windows(path: Path, requested_windows: int, window_sec: float, top_k: int) -> list[dict[str, Any]]:
    raw = read_raw(path, preload=False)
    sfreq = float(raw.info["sfreq"])
    duration_sec = float(raw.n_times / sfreq)
    channels = _pick_channels(list(raw.ch_names), ",".join(DEFAULT_CHANNELS))
    picks = raw.copy().pick(channels)
    window_sec = min(max(float(window_sec), 1.0), 30.0)
    requested_windows = max(8, min(int(requested_windows), MAX_SCAN_WINDOWS))
    top_k = max(1, min(int(top_k), 40))
    if duration_sec <= window_sec:
        starts = [0.0]
    else:
        scan_stop = max(0.0, duration_sec - window_sec)
        starts = np.linspace(0.0, scan_stop, num=requested_windows).tolist()

    scored: list[dict[str, Any]] = []
    for start_sec in starts:
        start_sample = int(max(0.0, start_sec) * sfreq)
        stop_sample = min(raw.n_times, max(start_sample + 1, int((start_sec + window_sec) * sfreq)))
        data = picks.get_data(start=start_sample, stop=stop_sample)
        data = _scale_to_uv(np.asarray(data, dtype=float))
        finite = data[np.isfinite(data)]
        if finite.size == 0:
            continue
        rms = float(np.sqrt(np.nanmean(np.square(finite))))
        ptp = float(np.nanpercentile(finite, 99) - np.nanpercentile(finite, 1))
        scored.append(
            {
                "start_sec": round(float(start_sec), 3),
                "duration_sec": round((stop_sample - start_sample) / sfreq, 3),
                "rms_uv": round(rms, 4),
                "ptp_uv": round(ptp, 4),
                "preview_rms_ptp_rank_score": _metric_score(rms, ptp),
            }
        )

    scored.sort(key=lambda item: (item["preview_rms_ptp_rank_score"], item["ptp_uv"], item["rms_uv"]), reverse=True)
    candidates: list[dict[str, Any]] = []
    for index, item in enumerate(scored[:top_k], start=1):
        event_id = f"{path.stem.upper()}-SCAN-{index:03d}"
        duration = max(1.0, float(item["duration_sec"]))
        candidates.append(
            {
                "event_id": event_id,
                "id": event_id,
                "index": index,
                "start_sec": item["start_sec"],
                "end_sec": round(item["start_sec"] + duration, 3),
                "duration_sec": duration,
                "event_type": "candidate_window",
                "priority": "high" if item["preview_rms_ptp_rank_score"] >= 0.9 else "medium",
                "channels": channels,
                "preview_rms_ptp_rank_score": item["preview_rms_ptp_rank_score"],
                "score_kind": "bounded_scan_rms_ptp_rank_not_probability",
                "score_note": "有限均匀窗口抽样后的 RMS/PTP 复核优先级排序值，不是临床概率、检测置信度、敏感性/特异性或诊断结论。",
                "backend_metrics": {
                    "rms_uv": item["rms_uv"],
                    "ptp_uv": item["ptp_uv"],
                    "preview_rms_ptp_rank_score": item["preview_rms_ptp_rank_score"],
                },
                "source": "bounded_full_record_window_scan_metrics",
                "event_type_scope": "candidate_window_only",
                "evidence_window": {
                    "start_sec": item["start_sec"],
                    "duration_sec": duration,
                    "channels": channels,
                },
            }
        )
    return candidates


def _seeded_candidates(path: Path, record_id: str) -> list[dict[str, Any]]:
    seeds = HE_CANDIDATE_SEEDS.get(record_id, [])
    candidates = []
    for index, seed in enumerate(seeds, start=1):
        metrics = _candidate_metrics(path, seed)
        preview_score = metrics["preview_rms_ptp_rank_score"]
        candidates.append({
            **seed,
            "id": seed["event_id"],
            "index": index,
            "preview_rms_ptp_rank_score": preview_score,
            "score_kind": "preview_rms_ptp_rank_not_probability",
            "score_note": "RMS/PTP 小窗口复核优先级排序值，不是临床概率、检测置信度、敏感性/特异性或诊断结论。",
            "backend_metrics": metrics,
            "source": "seeded_time_real_edf_window_metrics",
            "event_type_scope": "candidate_label_only",
            "evidence_window": {
                "start_sec": max(0.0, float(seed["start_sec"]) - 10.0),
                "duration_sec": min(30.0, float(seed["duration_sec"]) + 20.0),
                "channels": DEFAULT_CHANNELS,
            },
        })
    return candidates


@router.get("/lab/epilepsy-full-flow/records")
def list_he_records(request: Request, inspect: bool = Query(False)) -> dict[str, Any]:
    records = [_record_payload(path, request, include_metadata=inspect) for path in _sample_paths()]
    return {
        "root": SAFE_SAMPLE_ROOT,
        "safe_root": SAFE_SAMPLE_ROOT,
        "is_local_request": _is_local_request(request),
        "path_visibility": "safe_relative",
        "records": records,
        "non_medical_scope": "research_screening_support_only",
    }


@router.get("/lab/epilepsy-full-flow/records/{record_id}/preflight")
def preflight_he_record(record_id: str, request: Request) -> dict[str, Any]:
    path = _sample_path(record_id)
    record = _record_payload(path, request, include_metadata=True)
    record["preflight"] = {
        "status": "pass",
        "reader": "mne_preload_false",
        "large_file_strategy": "windowed_reading_only",
        "browser_full_load_allowed": False,
        "candidate_generation": "bounded_full_record_window_scan_rms_ptp_v1",
        "report_boundary": "research_screening_support_only",
    }
    return record


@router.post("/lab/epilepsy-full-flow/records/{record_id}/candidates")
def generate_he_candidates(
    record_id: str,
    request: Request,
    scan_windows: int = Query(DEFAULT_SCAN_WINDOWS, ge=8, le=MAX_SCAN_WINDOWS),
    window_sec: float = Query(DEFAULT_SCAN_WINDOW_SEC, ge=1.0, le=30.0),
    top_k: int = Query(DEFAULT_SCAN_TOP_K, ge=1, le=40),
    allow_seeded_fallback: bool = Query(False),
) -> dict[str, Any]:
    path = _sample_path(record_id)
    record = _record_payload(path, request, include_metadata=True)
    fallback_reason = ""
    try:
        candidates = _scan_candidate_windows(path, scan_windows, window_sec, top_k)
        candidate_source = "bounded_full_record_window_scan_rms_ptp_v1"
        algorithm_status = "lab_bounded_scan_not_validated_detector"
    except Exception as exc:
        if not allow_seeded_fallback:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "candidate_scan_failed",
                    "message": "Real bounded EDF candidate scan failed; seeded fallback is disabled by default.",
                    "fallback_allowed": False,
                    "non_medical_scope": "research_screening_support_only",
                },
            ) from exc
        candidates = _seeded_candidates(path, record_id)
        fallback_reason = _safe_exception_summary(exc)
        candidate_source = "fallback_seeded_candidate_times_with_real_edf_window_metrics_v2"
        algorithm_status = "lab_preview_seed_fallback_not_validated_detector"
    return {
        "record": record,
        "candidates": candidates,
        "candidate_source": candidate_source,
        "algorithm_status": algorithm_status,
        "scan_parameters": {
            "scan_windows": scan_windows,
            "window_sec": window_sec,
            "top_k": top_k,
            "allow_seeded_fallback": allow_seeded_fallback,
            "strategy": "uniform_full_record_window_sampling_ranked_by_rms_ptp",
        },
        "fallback_reason": fallback_reason,
        "limitations": [
            "候选片段按真实 EDF 波形窗口的 RMS/PTP 预览指标排序，不是模型概率。",
            "当前有限窗口扫描不是完整检测器，不能估计敏感性、特异性或漏检率。",
            "正式交付仍需要真实图表材料、可追溯复核记录和导出清单。",
        ],
        "candidate_boundary_notes": [
            "系统按有限均匀采样读取全记录中的真实 EDF 窗口，并按 RMS/PTP 排序。",
            "当前流程不是经外部验证的完整检测器。",
            "正式交付必须补齐真实图表材料和可追溯复核清单。",
        ],
        "non_medical_scope": "research_screening_support_only",
    }


@router.get("/lab/epilepsy-full-flow/records/{record_id}/waveform-window")
def he_waveform_window(
    record_id: str,
    start_sec: float = Query(0.0, ge=0.0),
    duration_sec: float = Query(30.0, gt=0.0, le=MAX_WAVEFORM_DURATION_SEC),
    channels: str = Query("EEG1,EEG2,EMG,ACC"),
    max_points: int = Query(2000, ge=100, le=MAX_WAVEFORM_POINTS),
) -> dict[str, Any]:
    path = _sample_path(record_id)
    return _window_data_cached(path, start_sec=start_sec, duration_sec=duration_sec, channels=channels, max_points=max_points)


@router.post("/lab/epilepsy-full-flow/review-sessions")
def save_lab_review_session(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    payload_chars = len(str(payload))
    if payload_chars > MAX_REVIEW_PAYLOAD_CHARS:
        raise HTTPException(status_code=413, detail=f"review session payload exceeds {MAX_REVIEW_PAYLOAD_CHARS} characters")
    if payload.get("non_medical_scope") != "research_screening_support_only":
        raise HTTPException(status_code=422, detail="non_medical_scope must be research_screening_support_only")
    record = payload.get("record") or {}
    events = payload.get("reviewed_events") or []
    actions = payload.get("actions") or []
    if not isinstance(record, dict):
        raise HTTPException(status_code=422, detail="record must be an object")
    if not record.get("filename"):
        raise HTTPException(status_code=422, detail="record.filename is required")
    events = _require_object_list(events, "reviewed_events", MAX_REVIEW_EVENTS)
    actions = _require_object_list(actions, "actions", MAX_REVIEW_ACTIONS)
    normalized_events = [_normalize_review_event(item) for item in events[:MAX_REVIEW_EVENTS]]
    session_id = f"lab_ep_review_{uuid4().hex[:12]}"
    saved_at = datetime.now(timezone.utc).isoformat()
    stored = {
        "session_id": session_id,
        "saved_at": saved_at,
        "generated_at": _sanitize_payload(payload.get("generated_at") or payload.get("created_at")),
        "schema_version": payload.get("schema_version"),
        "review_session_schema_version": payload.get("review_session_schema_version"),
        "non_medical_scope": payload.get("non_medical_scope"),
        "record": _sanitized_record(record),
        "context": _sanitize_payload(payload.get("context") or {}),
        "model": _sanitize_payload(payload.get("model") or {}),
        "summary": _sanitize_payload(payload.get("summary") or {}),
        "event_reviews": _sanitize_payload(payload.get("event_reviews") or {}),
        "reviewed_events": _sanitize_payload(normalized_events),
        "actions": _sanitize_payload(actions[-MAX_REVIEW_ACTIONS:]),
        "source": "lab_epilepsy_full_flow_backend_file_sanitized",
        "storage": "local_lab_json_file",
    }
    LAB_REVIEW_SESSIONS[session_id] = stored
    LAB_REVIEW_SESSIONS.move_to_end(session_id)
    while len(LAB_REVIEW_SESSIONS) > MAX_REVIEW_SESSIONS:
        LAB_REVIEW_SESSIONS.popitem(last=False)
    _persist_review_session(stored)
    return {
        "session_id": session_id,
        "saved_at": saved_at,
        "record_filename": record.get("filename"),
        "event_count": len(normalized_events),
        "reviewed_count": sum(1 for item in normalized_events if _event_review_status(item) != "unreviewed"),
        "source": stored["source"],
        "non_medical_scope": stored["non_medical_scope"],
    }


@router.get("/lab/epilepsy-full-flow/review-sessions/{session_id}")
def get_lab_review_session(session_id: str) -> dict[str, Any]:
    session = _load_review_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Lab review session not found")
    return session


@router.post("/lab/epilepsy-full-flow/review-sessions/{session_id}/exports")
def export_lab_review_session(session_id: str) -> dict[str, Any]:
    session = _load_review_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Lab review session not found")
    return _lab_review_export(session)


@router.get("/lab/epilepsy-full-flow/review-sessions/{session_id}/report")
def report_lab_review_session(session_id: str) -> dict[str, Any]:
    session = _load_review_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Lab review session not found")
    return _lab_review_report(session)
