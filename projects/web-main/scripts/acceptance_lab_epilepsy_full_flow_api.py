from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "work" / "release_evidence" / "lab_epilepsy_full_flow_api"

REQUIRED_OPENAPI_PATHS = {
    "/api/lab/epilepsy-full-flow/records": {"get"},
    "/api/lab/epilepsy-full-flow/records/{record_id}/preflight": {"get"},
    "/api/lab/epilepsy-full-flow/records/{record_id}/candidates": {"post"},
    "/api/lab/epilepsy-full-flow/records/{record_id}/waveform-window": {"get"},
    "/api/lab/epilepsy-full-flow/review-sessions": {"post"},
    "/api/lab/epilepsy-full-flow/review-sessions/{session_id}": {"get"},
    "/api/lab/epilepsy-full-flow/review-sessions/{session_id}/exports": {"post"},
    "/api/lab/epilepsy-full-flow/review-sessions/{session_id}/report": {"get"},
}

OLD_CUSTOMER_COPY_TERMS = [
    "人工保留",
    "排除候选",
    "人工矫正",
    "复核包",
    "复核草稿数据包",
    "保留候选",
    "矫正模式",
    "人工修改",
    "候选集完整性未知",
    "图表证据",
    "保留事件",
    "后端 HE API",
    "demo=1",
    "前端内置样本",
    "reviewed_events.csv",
    "Legacy renderer",
    "Main preview",
    "Open this page",
    "Back to Analysis",
    "Canvas preview",
]


class AcceptanceFailure(AssertionError):
    pass


def now_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def normalize_api_base(value: str) -> str:
    return value.rstrip("/")


def root_url(api_base_url: str) -> str:
    return api_base_url[:-4] if api_base_url.endswith("/api") else api_base_url


def assert_ok(condition: bool, code: str, detail: Any = None) -> None:
    if not condition:
        raise AcceptanceFailure(f"{code}: {detail}")


def request_json(
    method: str,
    api_base_url: str,
    path: str,
    *,
    timeout: float,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    url = f"{api_base_url}{path}"
    if query:
        encoded = urllib.parse.urlencode({key: value for key, value in query.items() if value is not None})
        url = f"{url}?{encoded}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    started = time.perf_counter()
    request = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            payload = json.loads(raw) if raw else {}
            meta = {"method": method.upper(), "url": url, "status": response.status, "elapsed_ms": elapsed_ms}
            return payload, meta
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise AcceptanceFailure(f"HTTP {exc.code} {method.upper()} {url}: {raw}") from exc
    except Exception as exc:
        raise AcceptanceFailure(f"{method.upper()} {url} failed: {exc}") from exc


def request_json_error(
    method: str,
    api_base_url: str,
    path: str,
    *,
    timeout: float,
    expected_status: int,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    url = f"{api_base_url}{path}"
    if query:
        encoded = urllib.parse.urlencode({key: value for key, value in query.items() if value is not None})
        url = f"{url}?{encoded}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            raise AcceptanceFailure(f"Expected HTTP {expected_status} for {method.upper()} {url}, got {response.status}: {raw}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(raw) if raw else {}
        assert_ok(exc.code == expected_status, "UNEXPECTED_HTTP_ERROR_STATUS", {"expected": expected_status, "actual": exc.code, "payload": payload})
        return payload, {"method": method.upper(), "url": url, "status": exc.code}
    except Exception as exc:
        raise AcceptanceFailure(f"{method.upper()} {url} failed: {exc}") from exc


def get_openapi(api_base_url: str, timeout: float) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    url = f"{root_url(api_base_url)}/openapi.json"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw), {
                "method": "GET",
                "url": url,
                "status": response.status,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            }
    except Exception as exc:
        raise AcceptanceFailure(f"GET {url} failed: {exc}") from exc


def validate_lab_openapi(openapi: dict[str, Any]) -> dict[str, Any]:
    paths = openapi.get("paths", {}) if isinstance(openapi, dict) else {}
    endpoint_results: dict[str, dict[str, Any]] = {}
    for path, required_methods in REQUIRED_OPENAPI_PATHS.items():
        actual_methods = set(paths.get(path, {}).keys())
        endpoint_results[path] = {
            "required_methods": sorted(required_methods),
            "actual_methods": sorted(actual_methods),
            "ok": required_methods.issubset(actual_methods),
        }
    missing = [path for path, result in endpoint_results.items() if not result["ok"]]
    assert_ok(not missing, "LAB_EPILEPSY_FULL_FLOW_ROUTES_MISSING", endpoint_results)
    return endpoint_results


def write_step(evidence_dir: Path, name: str, payload: Any) -> None:
    (evidence_dir / f"{name}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def number_or(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed == parsed else fallback


def safe_channels(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.split(",") if part.strip()]
    return ["EEG1", "EEG2"]


def assert_waveform_contract(waveform: dict[str, Any], max_points: int) -> None:
    channels = waveform.get("channels")
    assert_ok(isinstance(channels, list) and channels, "WAVEFORM_CHANNELS_EMPTY", waveform)
    for channel in channels:
        assert_ok(isinstance(channel, dict), "WAVEFORM_CHANNEL_NOT_OBJECT", channel)
        times = channel.get("times_sec")
        values = channel.get("values")
        assert_ok(isinstance(times, list) and len(times) >= 2, "WAVEFORM_TIMES_INVALID", channel)
        assert_ok(isinstance(values, list), "WAVEFORM_CHANNEL_VALUES_MISSING", channel)
        numeric_times = [number_or(item, float("nan")) for item in times]
        assert_ok(all(item == item for item in numeric_times), "WAVEFORM_TIMES_NOT_NUMERIC", times[:10])
        assert_ok(all(numeric_times[index] < numeric_times[index + 1] for index in range(len(numeric_times) - 1)), "WAVEFORM_TIMES_NOT_MONOTONIC", times[:10])
        assert_ok(len(numeric_times) <= max_points, "WAVEFORM_MAX_POINTS_NOT_ENFORCED", {"channel": channel.get("name"), "points": len(numeric_times), "max_points": max_points})
        assert_ok(len(values) == len(numeric_times), "WAVEFORM_CHANNEL_LENGTH_MISMATCH", {"channel": channel.get("name"), "values": len(values), "times": len(numeric_times)})
    assert_ok((waveform.get("unit") or "uV") == "uV", "WAVEFORM_UNIT_INVALID", waveform.get("unit"))


def event_status_for_index(index: int) -> str:
    if index == 0:
        return "confirmed"
    if index == 1:
        return "rejected"
    if index == 2:
        return "needs_review"
    return "unreviewed"


def normalize_event(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    start = number_or(candidate.get("start_sec"), 0.0)
    duration = number_or(candidate.get("duration_sec"), 2.0)
    end = number_or(candidate.get("end_sec"), start + duration)
    if end <= start:
        end = start + max(0.2, duration)
    original_start = start
    original_end = end
    if index == 0:
        start += 0.5
        end += 0.5
    event_id = str(candidate.get("event_id") or candidate.get("id") or f"candidate_{index + 1:03d}")
    status = event_status_for_index(index)
    raw_window = candidate.get("evidence_window") if isinstance(candidate.get("evidence_window"), dict) else None
    evidence_window = None
    if raw_window:
        evidence_window = {
            "start_sec": raw_window.get("start_sec"),
            "duration_sec": raw_window.get("duration_sec"),
            "channels": safe_channels(raw_window.get("channels") or candidate.get("channels")),
            "unit": raw_window.get("unit") or "uV",
        }
    return {
        "event_id": event_id,
        "status": status,
        "event_type": candidate.get("event_type") or candidate.get("ai_type") or "candidate_window",
        "start_sec": round(start, 3),
        "end_sec": round(end, 3),
        "duration_sec": round(end - start, 3),
        "original_start_sec": round(original_start, 3),
        "original_end_sec": round(original_end, 3),
        "channels": safe_channels(candidate.get("channels")),
        "evidence_window": evidence_window,
        "evidence_grade": "B" if status == "confirmed" else "C",
        "review_note": {
            "confirmed": "验收脚本：纳入草稿候选，用于验证报告草稿链路。",
            "rejected": "验收脚本：不纳入草稿，用于验证排除类候选不会进入结论。",
            "needs_review": "验收脚本：存疑候选，用于验证部分复核状态。",
            "unreviewed": "",
        }[status],
        "reviewer": "acceptance_script",
        "reviewed_at": datetime.now().isoformat() if status != "unreviewed" else "",
        "preview_rms_ptp_rank_score": number_or(
            candidate.get("preview_rms_ptp_rank_score", candidate.get("score")),
            0.0,
        ),
        "score_kind": candidate.get("score_kind") or "preview_rank_not_probability",
        "score_note": candidate.get("score_note") or "排序值不是候选为真实事件的概率、检测置信度或确定性结论。",
        "event_source": candidate.get("source") or "bounded_full_record_window_scan_rms_ptp_v1",
    }


def build_review_payload(record: dict[str, Any], candidates: list[dict[str, Any]], candidate_source: str, algorithm_status: str, scan_parameters: dict[str, Any]) -> dict[str, Any]:
    events = [normalize_event(candidate, index) for index, candidate in enumerate(candidates)]
    reviewed_count = sum(1 for event in events if event["status"] != "unreviewed")
    return {
        "schema_version": "qlanalyser.epilepsy.manual_correction_preview.v1",
        "review_session_schema_version": "qlanalyser.epilepsy.review_session.v1",
        "non_medical_scope": "research_screening_support_only",
        "created_at": datetime.now().isoformat(),
        "record": {
            "id": record.get("id") or "",
            "record_id": record.get("id") or record.get("record_id") or "",
            "file_id": record.get("file_id") or record.get("id") or "",
            "filename": record.get("filename") or "",
            "size_bytes": record.get("size_bytes"),
            "duration_sec": number_or(record.get("duration_sec"), 0.0),
            "sfreq": record.get("sfreq"),
            "channels": record.get("channels") or [],
            "safe_source_path": record.get("safe_source_path") or f"HE示例数据/{record.get('filename', '')}",
            "path_visibility": "safe_relative",
        },
        "metadata": {
            "review_event_source": "reviewed_events",
            "has_full_candidate_set": True,
            "has_explicit_candidate_denominator": True,
            "candidate_denominator": len(events),
            "denominator_note": "本复核记录包含当前验收脚本收到的完整候选队列。",
        },
        "context": {
            "workflow_id": "epilepsy_full_flow_preview",
            "task_id": f"acceptance_{record.get('id') or 'he'}",
            "input_file_id": record.get("file_id") or record.get("id") or "",
            "review_session_id": f"acceptance_session_{record.get('id') or 'he'}",
            "source_algorithm_artifact_id": candidate_source,
            "source_page": "acceptance_lab_epilepsy_full_flow_api",
            "scan_parameters": scan_parameters,
        },
        "model": {
            "detector_version": algorithm_status or "lab_preview_detector",
            "threshold": None,
            "note": "候选仅用于科研筛查复核流程验证，不是外部验证过的正式检测器输出。",
        },
        "summary": {
            "auto_candidates": len(events),
            "reviewed": reviewed_count,
            "confirmed": sum(1 for event in events if event["status"] == "confirmed"),
            "rejected": sum(1 for event in events if event["status"] == "rejected"),
            "needs_review": sum(1 for event in events if event["status"] == "needs_review"),
            "unreviewed": sum(1 for event in events if event["status"] == "unreviewed"),
        },
        "event_reviews": {
            event["event_id"]: {
                "status": event["status"],
                "reviewed_type": event["event_type"],
                "evidence_grade": event["evidence_grade"],
                "adjusted_start_sec": event["start_sec"],
                "adjusted_end_sec": event["end_sec"],
                "note": event["review_note"],
                "reviewer": event["reviewer"],
                "reviewed_at": event["reviewed_at"],
            }
            for event in events
        },
        "reviewed_events": events,
        "actions": [
            {
                "action": "acceptance_partial_review",
                "detail": "API验收脚本生成一个部分复核草稿，验证候选分母、导出和报告边界。",
                "created_at": datetime.now().isoformat(),
                "source": "acceptance_script",
            }
        ],
    }


def scan_customer_text(export_payload: dict[str, Any], report_payload: dict[str, Any]) -> dict[str, list[str]]:
    text_parts = [
        str(export_payload.get("download_class", "")),
        json.dumps(export_payload.get("summary_json", {}), ensure_ascii=False),
        json.dumps(export_payload.get("scope_contract_json", {}), ensure_ascii=False),
        str(export_payload.get("final_review_events_csv", ""))[:3000],
        str(report_payload.get("report_status", "")),
        str(report_payload.get("interpretation", "")),
        str(report_payload.get("methods", "")),
        json.dumps(report_payload.get("figure_manifest", []), ensure_ascii=False),
    ]
    text = "\n".join(text_parts)
    return {term: [line for line in text.splitlines() if term in line][:3] for term in OLD_CUSTOMER_COPY_TERMS if term in text}


def run_acceptance(args: argparse.Namespace) -> dict[str, Any]:
    api_base_url = normalize_api_base(args.api_base_url)
    run_id = now_run_id()
    evidence_dir = args.evidence_root / run_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "schema_version": "qlanalyser.lab_epilepsy_full_flow_api_acceptance.v1",
        "run_id": run_id,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "api_base_url": api_base_url,
        "evidence_dir": str(evidence_dir),
        "checks": [],
        "timings_ms": {},
    }

    def record(name: str, detail: Any = None) -> None:
        result["checks"].append({"name": name, "status": "passed", "detail": detail})

    openapi, meta = get_openapi(api_base_url, args.timeout)
    result["timings_ms"]["openapi"] = meta["elapsed_ms"]
    endpoint_results = validate_lab_openapi(openapi)
    write_step(evidence_dir, "openapi_epilepsy_full_flow_paths", endpoint_results)
    record("lab_epilepsy_full_flow_routes_present", {"path_count": len(openapi.get("paths", {}))})

    records_payload, meta = request_json("GET", api_base_url, "/lab/epilepsy-full-flow/records", timeout=args.timeout, query={"inspect": "true"})
    result["timings_ms"]["records"] = meta["elapsed_ms"]
    records = records_payload.get("records") if isinstance(records_payload, dict) else []
    assert_ok(isinstance(records, list) and records, "HE_RECORDS_EMPTY", records_payload)
    record_id = args.record_id or str(records[0].get("id") or records[0].get("record_id") or "")
    selected_record = next((item for item in records if str(item.get("id") or item.get("record_id")) == record_id), None)
    assert_ok(selected_record is not None and record_id, "SELECTED_RECORD_NOT_FOUND", {"record_id": record_id, "available": [item.get("id") for item in records]})
    write_step(evidence_dir, "records", records_payload)
    record("he_records_loaded", {"record_count": len(records), "selected_record_id": record_id, "filename": selected_record.get("filename")})

    preflight, meta = request_json("GET", api_base_url, f"/lab/epilepsy-full-flow/records/{urllib.parse.quote(record_id)}/preflight", timeout=args.timeout)
    result["timings_ms"]["preflight"] = meta["elapsed_ms"]
    assert_ok((preflight.get("preflight") or {}).get("status") == "pass", "PREFLIGHT_NOT_PASS", preflight.get("preflight"))
    assert_ok(number_or(preflight.get("duration_sec"), 0.0) > 0, "PREFLIGHT_DURATION_MISSING", preflight)
    assert_ok(number_or(preflight.get("sfreq"), 0.0) > 0, "PREFLIGHT_SFREQ_MISSING", preflight)
    write_step(evidence_dir, "preflight", preflight)
    record("preflight_passed", {"sfreq": preflight.get("sfreq"), "duration_sec": preflight.get("duration_sec"), "channel_count": preflight.get("channel_count")})

    candidate_query = {"scan_windows": args.scan_windows, "window_sec": args.window_sec, "top_k": args.top_k}
    if args.allow_seeded_fallback:
        candidate_query["allow_seeded_fallback"] = "true"
    candidates_payload, meta = request_json("POST", api_base_url, f"/lab/epilepsy-full-flow/records/{urllib.parse.quote(record_id)}/candidates", timeout=args.candidate_timeout, query=candidate_query)
    result["timings_ms"]["candidates"] = meta["elapsed_ms"]
    candidates = candidates_payload.get("candidates") if isinstance(candidates_payload, dict) else []
    assert_ok(isinstance(candidates, list) and candidates, "CANDIDATES_EMPTY", candidates_payload)
    assert_ok(candidates_payload.get("non_medical_scope") == "research_screening_support_only", "CANDIDATE_SCOPE_INVALID", candidates_payload.get("non_medical_scope"))
    assert_ok(candidates_payload.get("candidate_source") == "bounded_full_record_window_scan_rms_ptp_v1", "CANDIDATE_SOURCE_NOT_REAL_SCAN", candidates_payload.get("candidate_source"))
    assert_ok("fallback" not in str(candidates_payload.get("algorithm_status", "")).lower(), "CANDIDATE_ALGORITHM_STATUS_FALLBACK", candidates_payload.get("algorithm_status"))
    if not args.allow_seeded_fallback:
        assert_ok(not candidates_payload.get("fallback_reason"), "CANDIDATE_FALLBACK_OCCURRED", {
            "candidate_source": candidates_payload.get("candidate_source"),
            "fallback_reason": candidates_payload.get("fallback_reason"),
        })
    write_step(evidence_dir, "candidates", candidates_payload)
    record("candidates_generated", {"candidate_count": len(candidates), "candidate_source": candidates_payload.get("candidate_source"), "algorithm_status": candidates_payload.get("algorithm_status")})

    first_event = normalize_event(candidates[0], 0)
    waveform_query = {
        "start_sec": max(0.0, first_event["start_sec"] - 5.0),
        "duration_sec": min(30.0, first_event["duration_sec"] + 10.0),
        "channels": ",".join(first_event["channels"][:4]),
        "max_points": 1200,
    }
    waveform, meta = request_json("GET", api_base_url, f"/lab/epilepsy-full-flow/records/{urllib.parse.quote(record_id)}/waveform-window", timeout=args.timeout, query=waveform_query)
    result["timings_ms"]["waveform_window"] = meta["elapsed_ms"]
    assert_ok(number_or(waveform.get("duration_sec"), 0.0) > 0, "WAVEFORM_DURATION_MISSING", waveform)
    assert_waveform_contract(waveform, int(waveform_query["max_points"]))
    write_step(evidence_dir, "waveform_window", waveform)
    record("waveform_window_loaded", {"channel_count": len(waveform.get("channels", [])), "duration_sec": waveform.get("duration_sec"), "start_sec": waveform.get("start_sec")})

    review_payload = build_review_payload(
        preflight,
        candidates,
        str(candidates_payload.get("candidate_source") or ""),
        str(candidates_payload.get("algorithm_status") or ""),
        candidates_payload.get("scan_parameters") or {},
    )
    write_step(evidence_dir, "review_payload", review_payload)
    blocked_reviewer_results = []
    for blocked_reviewer in ("preview_reviewer", "trial_research_reviewer", "demo_autofill_reviewer"):
        blocked_reviewer_payload = deepcopy(review_payload)
        for event in blocked_reviewer_payload["reviewed_events"]:
            if event["status"] != "unreviewed":
                event["reviewer"] = blocked_reviewer
                break
        blocked_reviewer_error, blocked_reviewer_meta = request_json_error(
            "POST",
            api_base_url,
            "/lab/epilepsy-full-flow/review-sessions",
            timeout=args.timeout,
            expected_status=422,
            body=blocked_reviewer_payload,
        )
        assert_ok((blocked_reviewer_error.get("detail") or {}).get("code") == "reviewer_placeholder_not_allowed", "BLOCKED_REVIEWER_ERROR_CODE_INVALID", blocked_reviewer_error)
        blocked_reviewer_results.append({"reviewer": blocked_reviewer, "meta": blocked_reviewer_meta, "payload": blocked_reviewer_error})
    write_step(evidence_dir, "reviewer_placeholders_rejected", blocked_reviewer_results)
    record("reviewer_placeholders_rejected", blocked_reviewer_results)

    unreviewed_reviewer_payload = deepcopy(review_payload)
    unreviewed_event_id = ""
    for event in unreviewed_reviewer_payload["reviewed_events"]:
        if event["status"] == "unreviewed":
            event["reviewer"] = "demo_autofill_reviewer"
            event["evidence_grade"] = "B"
            event["reviewed_at"] = datetime.now().isoformat()
            unreviewed_event_id = event["event_id"]
            break
    assert_ok(bool(unreviewed_event_id), "UNREVIEWED_PLACEHOLDER_TEST_EVENT_MISSING", unreviewed_reviewer_payload["reviewed_events"])
    unreviewed_session, _ = request_json("POST", api_base_url, "/lab/epilepsy-full-flow/review-sessions", timeout=args.timeout, body=unreviewed_reviewer_payload)
    unreviewed_session_id = str(unreviewed_session.get("session_id") or "")
    unreviewed_readback, _ = request_json("GET", api_base_url, f"/lab/epilepsy-full-flow/review-sessions/{urllib.parse.quote(unreviewed_session_id)}", timeout=args.timeout)
    unreviewed_export, _ = request_json("POST", api_base_url, f"/lab/epilepsy-full-flow/review-sessions/{urllib.parse.quote(unreviewed_session_id)}/exports", timeout=args.timeout)
    cleaned_unreviewed = next((event for event in (unreviewed_readback.get("reviewed_events") or []) if event.get("event_id") == unreviewed_event_id), {})
    assert_ok(cleaned_unreviewed.get("reviewer", "") == "", "UNREVIEWED_REVIEWER_NOT_CLEARED", cleaned_unreviewed)
    assert_ok(cleaned_unreviewed.get("evidence_grade", "") == "", "UNREVIEWED_EVIDENCE_GRADE_NOT_CLEARED", cleaned_unreviewed)
    assert_ok("demo_autofill_reviewer" not in json.dumps(unreviewed_export, ensure_ascii=False), "UNREVIEWED_PLACEHOLDER_LEAKED_TO_EXPORT", unreviewed_export)
    write_step(evidence_dir, "unreviewed_reviewer_cleared", {"session": unreviewed_session, "readback": unreviewed_readback, "export": unreviewed_export})
    record("unreviewed_reviewer_cleared", {"session_id": unreviewed_session_id, "event_id": unreviewed_event_id})

    missing_evidence_payload = deepcopy(review_payload)
    for event in missing_evidence_payload["reviewed_events"]:
        if event["status"] != "unreviewed":
            event["evidence_window"] = None
            break
    missing_session, missing_meta = request_json("POST", api_base_url, "/lab/epilepsy-full-flow/review-sessions", timeout=args.timeout, body=missing_evidence_payload)
    missing_session_id = str(missing_session.get("session_id") or "")
    missing_export, _ = request_json("POST", api_base_url, f"/lab/epilepsy-full-flow/review-sessions/{urllib.parse.quote(missing_session_id)}/exports", timeout=args.timeout)
    missing_report, _ = request_json("GET", api_base_url, f"/lab/epilepsy-full-flow/review-sessions/{urllib.parse.quote(missing_session_id)}/report", timeout=args.timeout)
    missing_manifest = missing_export.get("manifest") or {}
    assert_ok(missing_export.get("evidence_ready") is False, "MISSING_EVIDENCE_EXPORT_READY_SHOULD_BE_FALSE", missing_export.get("event_evidence_manifest"))
    assert_ok(missing_report.get("report_readiness", {}).get("research_draft_ready") is False, "MISSING_EVIDENCE_REPORT_READY_SHOULD_BE_FALSE", missing_report.get("report_readiness"))
    assert_ok("backend_verified_waveform_evidence_required" in (missing_report.get("report_readiness", {}).get("blockers") or []), "MISSING_EVIDENCE_BLOCKER_MISSING", missing_report.get("report_readiness"))
    assert_ok(any(item.get("evidence_ready") is False for item in (missing_manifest.get("event_evidence_manifest") or [])), "MISSING_EVIDENCE_MANIFEST_NOT_FLAGGED", missing_manifest.get("event_evidence_manifest"))
    write_step(evidence_dir, "missing_evidence_not_ready", {"session": missing_session, "export": missing_export, "report": missing_report})
    record("missing_evidence_not_ready", {"session_id": missing_session_id, "blockers": missing_report.get("report_readiness", {}).get("blockers")})

    self_declared_evidence_payload = deepcopy(review_payload)
    self_declared_evidence_payload["record"] = {
        **self_declared_evidence_payload["record"],
        "id": "fake-record",
        "record_id": "fake-record",
        "file_id": "fake_file",
        "filename": "fake.edf",
    }
    for event in self_declared_evidence_payload["reviewed_events"]:
        if isinstance(event.get("evidence_window"), dict):
            event["evidence_window"]["source"] = "real_edf_window"
    self_declared_session, _ = request_json("POST", api_base_url, "/lab/epilepsy-full-flow/review-sessions", timeout=args.timeout, body=self_declared_evidence_payload)
    self_declared_session_id = str(self_declared_session.get("session_id") or "")
    self_declared_export, _ = request_json("POST", api_base_url, f"/lab/epilepsy-full-flow/review-sessions/{urllib.parse.quote(self_declared_session_id)}/exports", timeout=args.timeout)
    self_declared_manifest = self_declared_export.get("manifest") or {}
    assert_ok(self_declared_export.get("evidence_ready") is False, "SELF_DECLARED_EVIDENCE_READY_SHOULD_BE_FALSE", self_declared_manifest.get("event_evidence_manifest"))
    assert_ok(all((item.get("verification") or {}).get("record_registered") is False for item in (self_declared_manifest.get("event_evidence_manifest") or [])), "SELF_DECLARED_EVIDENCE_RECORD_SHOULD_NOT_BE_REGISTERED", self_declared_manifest.get("event_evidence_manifest"))
    write_step(evidence_dir, "self_declared_evidence_not_ready", {"session": self_declared_session, "export": self_declared_export})
    record("self_declared_evidence_not_ready", {"session_id": self_declared_session_id})

    session, meta = request_json("POST", api_base_url, "/lab/epilepsy-full-flow/review-sessions", timeout=args.timeout, body=review_payload)
    result["timings_ms"]["review_session"] = meta["elapsed_ms"]
    session_id = str(session.get("session_id") or "")
    assert_ok(session_id.startswith("lab_ep_review_"), "REVIEW_SESSION_ID_INVALID", session)
    assert_ok(session.get("event_count") == len(candidates), "REVIEW_SESSION_EVENT_COUNT_INVALID", session)
    assert_ok(session.get("non_medical_scope") == "research_screening_support_only", "REVIEW_SESSION_SCOPE_INVALID", session)
    write_step(evidence_dir, "review_session", session)
    record("review_session_saved", {"session_id": session_id, "event_count": session.get("event_count"), "reviewed_count": session.get("reviewed_count")})

    saved_session, meta = request_json("GET", api_base_url, f"/lab/epilepsy-full-flow/review-sessions/{urllib.parse.quote(session_id)}", timeout=args.timeout)
    result["timings_ms"]["review_session_readback"] = meta["elapsed_ms"]
    assert_ok((saved_session.get("record") or {}).get("path_visibility") == "safe_relative", "SESSION_PATH_VISIBILITY_INVALID", saved_session.get("record"))
    assert_ok((saved_session.get("context") or {}).get("review_session_id") == session_id, "SESSION_CONTEXT_ID_MISMATCH", saved_session.get("context"))
    for event in saved_session.get("reviewed_events") or []:
        if event.get("status") == "unreviewed":
            assert_ok(event.get("reviewer", "") == "", "SESSION_UNREVIEWED_REVIEWER_NOT_CLEARED", event)
            assert_ok(event.get("evidence_grade", "") == "", "SESSION_UNREVIEWED_EVIDENCE_GRADE_NOT_CLEARED", event)
    write_step(evidence_dir, "review_session_readback", saved_session)
    record("review_session_readback", {"storage": saved_session.get("storage"), "source": saved_session.get("source")})

    export_payload, meta = request_json("POST", api_base_url, f"/lab/epilepsy-full-flow/review-sessions/{urllib.parse.quote(session_id)}/exports", timeout=args.timeout)
    result["timings_ms"]["export"] = meta["elapsed_ms"]
    assert_ok(export_payload.get("schema_version") == "qlanalyser.epilepsy.lab_review_export.v1", "EXPORT_SCHEMA_INVALID", export_payload.get("schema_version"))
    assert_ok((export_payload.get("scope_contract_json") or {}).get("clinical_use_allowed") is False, "EXPORT_CLINICAL_SCOPE_INVALID", export_payload.get("scope_contract_json"))
    assert_ok("final_review_events_csv" in export_payload, "EXPORT_FINAL_CSV_MISSING", sorted(export_payload.keys()))
    assert_ok("reviewed_candidate_events_csv" in export_payload, "EXPORT_CUSTOMER_EVENT_CSV_ALIAS_MISSING", sorted(export_payload.keys()))
    assert_ok(export_payload.get("export_source") == "backend_review_session_export", "EXPORT_SOURCE_NOT_BACKEND", export_payload.get("export_source"))
    assert_ok(bool(export_payload.get("exported_at")), "EXPORT_EXPORTED_AT_MISSING", export_payload)
    manifest = export_payload.get("manifest") or export_payload.get("export_manifest_json") or {}
    assert_ok(manifest.get("schema_version") == "qlanalyser.epilepsy.review_export_manifest.v1", "EXPORT_MANIFEST_SCHEMA_INVALID", manifest)
    assert_ok(manifest.get("session_id") == session_id, "EXPORT_MANIFEST_SESSION_MISMATCH", manifest)
    assert_ok(bool(manifest.get("generated_at")) and bool(manifest.get("exported_at")), "EXPORT_MANIFEST_TIMES_MISSING", manifest)
    assert_ok(manifest.get("method_version") and manifest.get("parameter_version"), "EXPORT_MANIFEST_VERSION_MISSING", manifest)
    input_manifest = manifest.get("input_data_manifest") or {}
    assert_ok(input_manifest.get("record_identity_hash"), "EXPORT_INPUT_MANIFEST_HASH_MISSING", input_manifest)
    assert_ok(input_manifest.get("record_id") == record_id, "EXPORT_INPUT_RECORD_ID_INVALID", input_manifest)
    assert_ok(bool(input_manifest.get("file_id")), "EXPORT_INPUT_FILE_ID_MISSING", input_manifest)
    scan_manifest = manifest.get("scan_parameters") or {}
    assert_ok(scan_manifest.get("candidate_source") == "bounded_full_record_window_scan_rms_ptp_v1", "EXPORT_SCAN_SOURCE_INVALID", scan_manifest)
    qc_manifest = manifest.get("qc_manifest") or {}
    assert_ok(qc_manifest.get("schema_version") == "qlanalyser.epilepsy.qc_manifest.v1", "EXPORT_QC_MANIFEST_INVALID", qc_manifest)
    evidence_manifest = manifest.get("event_evidence_manifest") or []
    assert_ok(len(evidence_manifest) == len(candidates), "EXPORT_EVIDENCE_MANIFEST_COUNT_INVALID", {"evidence": len(evidence_manifest), "candidates": len(candidates)})
    assert_ok(all(item.get("evidence_kind") == "real_edf_waveform_window" for item in evidence_manifest), "EXPORT_EVIDENCE_NOT_REAL_WAVEFORM_WINDOW", evidence_manifest[:2])
    assert_ok(all(item.get("evidence_ready") is True for item in evidence_manifest), "EXPORT_EVIDENCE_READY_FALSE", evidence_manifest[:2])
    assert_ok(all(item.get("record_id") == record_id for item in evidence_manifest), "EXPORT_EVIDENCE_RECORD_ID_INVALID", evidence_manifest[:2])
    assert_ok(all(item.get("waveform_window_endpoint") for item in evidence_manifest), "EXPORT_EVIDENCE_ENDPOINT_MISSING", evidence_manifest[:2])
    assert_ok(all((item.get("waveform_window_query") or {}).get("start_sec") is not None and (item.get("waveform_window_query") or {}).get("duration_sec") for item in evidence_manifest), "EXPORT_EVIDENCE_QUERY_INCOMPLETE", evidence_manifest[:2])
    assert_ok(all((item.get("verification") or {}).get("source") == "backend_registered_edf_sample" for item in evidence_manifest), "EXPORT_EVIDENCE_NOT_BACKEND_VERIFIED", evidence_manifest[:2])
    saved_events_by_id = {event.get("event_id"): event for event in (saved_session.get("reviewed_events") or [])}
    for item in evidence_manifest:
        saved_event = saved_events_by_id.get(item.get("event_id")) or {}
        window = item.get("window") or {}
        assert_ok(abs(number_or(window.get("start_sec"), -1) - number_or(saved_event.get("start_sec"), -2)) < 1e-6, "EXPORT_EVIDENCE_WINDOW_START_MISMATCH", {"event": saved_event, "window": window})
        assert_ok(abs(number_or(window.get("stop_sec"), -1) - number_or(saved_event.get("end_sec"), -2)) < 1e-6, "EXPORT_EVIDENCE_WINDOW_END_MISMATCH", {"event": saved_event, "window": window})
    figure_manifest = manifest.get("figure_manifest") or []
    assert_ok(any(item.get("id") == "realWaveformWindows" and item.get("evidence_ready") is True for item in figure_manifest), "EXPORT_REAL_WAVEFORM_FIGURE_MISSING", figure_manifest)
    summary_json = export_payload.get("summary_json") or {}
    assert_ok(summary_json.get("review_status") in {"partial_review_draft", "review_draft_ready"}, "EXPORT_REVIEW_STATUS_ENUM_INVALID", summary_json)
    assert_ok(bool(summary_json.get("review_status_label")), "EXPORT_REVIEW_STATUS_LABEL_MISSING", summary_json)
    write_step(evidence_dir, "export", export_payload)
    record("export_contract_passed", {"schema_version": export_payload.get("schema_version"), "download_class": export_payload.get("download_class")})

    report_payload, meta = request_json("GET", api_base_url, f"/lab/epilepsy-full-flow/review-sessions/{urllib.parse.quote(session_id)}/report", timeout=args.timeout)
    result["timings_ms"]["report"] = meta["elapsed_ms"]
    assert_ok(report_payload.get("schema_version") == "qlanalyser.epilepsy.report_preview.v1", "REPORT_SCHEMA_INVALID", report_payload.get("schema_version"))
    assert_ok(report_payload.get("non_medical_scope") == "research_screening_support_only", "REPORT_SCOPE_INVALID", report_payload.get("non_medical_scope"))
    assert_ok(report_payload.get("report_status") in {"partial_review_draft", "review_draft_ready"}, "REPORT_STATUS_ENUM_INVALID", report_payload.get("report_status"))
    assert_ok(bool(report_payload.get("report_status_label")), "REPORT_STATUS_LABEL_MISSING", report_payload)
    assert_ok(report_payload.get("export_source") == "backend_review_session_report", "REPORT_SOURCE_NOT_BACKEND", report_payload.get("export_source"))
    assert_ok(report_payload.get("evidence_ready") is True, "REPORT_EVIDENCE_NOT_READY", report_payload.get("report_readiness"))
    report_readiness = report_payload.get("report_readiness") or {}
    assert_ok(report_readiness.get("figure_evidence_ready") is True, "REPORT_FIGURE_EVIDENCE_NOT_READY", report_readiness)
    assert_ok((report_payload.get("export_manifest_json") or {}).get("session_id") == session_id, "REPORT_MANIFEST_SESSION_MISMATCH", report_payload.get("export_manifest_json"))
    assert_ok("不作为" in report_payload.get("interpretation", "") or "科研筛查" in report_payload.get("interpretation", ""), "REPORT_BOUNDARY_COPY_MISSING", report_payload.get("interpretation"))
    write_step(evidence_dir, "report", report_payload)
    record("report_contract_passed", {"schema_version": report_payload.get("schema_version"), "report_status": report_payload.get("report_status")})

    bad_terms = scan_customer_text(export_payload, report_payload)
    assert_ok(not bad_terms, "OLD_CUSTOMER_COPY_TERMS_PRESENT", bad_terms)
    record("customer_copy_residue_scan_passed", {"term_count": len(OLD_CUSTOMER_COPY_TERMS)})

    result["status"] = "passed"
    result["finished_at"] = datetime.now().isoformat()
    result["selected_record_id"] = record_id
    result["session_id"] = session_id
    result["candidate_count"] = len(candidates)
    result["review_summary"] = review_payload["summary"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local HE epilepsy full-flow API acceptance chain against a running backend.")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8001/api")
    parser.add_argument("--record-id", default="")
    parser.add_argument("--scan-windows", type=int, default=12)
    parser.add_argument("--window-sec", type=float, default=6.0)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--candidate-timeout", type=float, default=90.0)
    parser.add_argument("--evidence-root", type=Path, default=EVIDENCE_ROOT)
    parser.add_argument("--allow-seeded-fallback", action="store_true", help="Allow seeded candidate fallback when the real bounded window scan fails.")
    args = parser.parse_args()

    evidence_dir: Path | None = None
    try:
        result = run_acceptance(args)
        evidence_dir = Path(result["evidence_dir"])
    except Exception as exc:
        run_id = now_run_id()
        evidence_dir = args.evidence_root / f"{run_id}_failed"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "schema_version": "qlanalyser.lab_epilepsy_full_flow_api_acceptance.v1",
            "run_id": run_id,
            "status": "failed",
            "api_base_url": normalize_api_base(args.api_base_url),
            "evidence_dir": str(evidence_dir),
            "error": str(exc),
            "finished_at": datetime.now().isoformat(),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        write_step(evidence_dir, "final_verdict", result)
        latest = args.evidence_root / "latest_final_verdict.json"
        latest.parent.mkdir(parents=True, exist_ok=True)
        latest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    write_step(evidence_dir, "final_verdict", result)
    latest = args.evidence_root / "latest_final_verdict.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
