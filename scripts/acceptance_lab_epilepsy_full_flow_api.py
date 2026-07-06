from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
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
    event_id = str(candidate.get("event_id") or candidate.get("id") or f"candidate_{index + 1:03d}")
    status = event_status_for_index(index)
    return {
        "event_id": event_id,
        "status": status,
        "event_type": candidate.get("event_type") or candidate.get("ai_type") or "candidate_window",
        "start_sec": round(start, 3),
        "end_sec": round(end, 3),
        "duration_sec": round(end - start, 3),
        "original_start_sec": round(start, 3),
        "original_end_sec": round(end, 3),
        "channels": safe_channels(candidate.get("channels")),
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
        "score_note": candidate.get("score_note") or "排序值不是概率、置信度或诊断结论。",
        "event_source": candidate.get("source") or "bounded_full_record_window_scan_rms_ptp_v1",
    }


def build_review_payload(record: dict[str, Any], candidates: list[dict[str, Any]], candidate_source: str, algorithm_status: str) -> dict[str, Any]:
    events = [normalize_event(candidate, index) for index, candidate in enumerate(candidates)]
    reviewed_count = sum(1 for event in events if event["status"] != "unreviewed")
    return {
        "schema_version": "qlanalyser.epilepsy.manual_correction_preview.v1",
        "review_session_schema_version": "qlanalyser.epilepsy.review_session.v1",
        "non_medical_scope": "research_screening_support_only",
        "created_at": datetime.now().isoformat(),
        "record": {
            "file_id": record.get("file_id") or record.get("id") or "",
            "filename": record.get("filename") or "",
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
        },
        "model": {
            "detector_version": algorithm_status or "lab_preview_detector",
            "threshold": None,
            "note": "候选仅用于科研筛查复核流程验证，不是外部验证过的诊断检测器输出。",
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
    candidates_payload, meta = request_json("POST", api_base_url, f"/lab/epilepsy-full-flow/records/{urllib.parse.quote(record_id)}/candidates", timeout=args.candidate_timeout, query=candidate_query)
    result["timings_ms"]["candidates"] = meta["elapsed_ms"]
    candidates = candidates_payload.get("candidates") if isinstance(candidates_payload, dict) else []
    assert_ok(isinstance(candidates, list) and candidates, "CANDIDATES_EMPTY", candidates_payload)
    assert_ok(candidates_payload.get("non_medical_scope") == "research_screening_support_only", "CANDIDATE_SCOPE_INVALID", candidates_payload.get("non_medical_scope"))
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
    assert_ok(isinstance(waveform.get("channels"), list) and waveform["channels"], "WAVEFORM_CHANNELS_EMPTY", waveform)
    assert_ok(number_or(waveform.get("duration_sec"), 0.0) > 0, "WAVEFORM_DURATION_MISSING", waveform)
    write_step(evidence_dir, "waveform_window", waveform)
    record("waveform_window_loaded", {"channel_count": len(waveform.get("channels", [])), "duration_sec": waveform.get("duration_sec"), "start_sec": waveform.get("start_sec")})

    review_payload = build_review_payload(
        preflight,
        candidates,
        str(candidates_payload.get("candidate_source") or ""),
        str(candidates_payload.get("algorithm_status") or ""),
    )
    write_step(evidence_dir, "review_payload", review_payload)
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
    write_step(evidence_dir, "review_session_readback", saved_session)
    record("review_session_readback", {"storage": saved_session.get("storage"), "source": saved_session.get("source")})

    export_payload, meta = request_json("POST", api_base_url, f"/lab/epilepsy-full-flow/review-sessions/{urllib.parse.quote(session_id)}/exports", timeout=args.timeout)
    result["timings_ms"]["export"] = meta["elapsed_ms"]
    assert_ok(export_payload.get("schema_version") == "qlanalyser.epilepsy.lab_review_export.v1", "EXPORT_SCHEMA_INVALID", export_payload.get("schema_version"))
    assert_ok((export_payload.get("scope_contract_json") or {}).get("clinical_use_allowed") is False, "EXPORT_CLINICAL_SCOPE_INVALID", export_payload.get("scope_contract_json"))
    assert_ok("final_review_events_csv" in export_payload, "EXPORT_FINAL_CSV_MISSING", sorted(export_payload.keys()))
    assert_ok("reviewed_candidate_events_csv" in export_payload, "EXPORT_CUSTOMER_EVENT_CSV_ALIAS_MISSING", sorted(export_payload.keys()))
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
    assert_ok("不作为" in report_payload.get("interpretation", "") or "不是临床结论" in report_payload.get("interpretation", ""), "REPORT_BOUNDARY_COPY_MISSING", report_payload.get("interpretation"))
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
