from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_PATH = ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-21-2122-p0-durable-epoch-set-checkpoint.json"
OUT_DIR = ROOT / "work" / "release_evidence" / "p0_gap_repair"
OUT_PATH = OUT_DIR / "acceptance_p0_gap_repair_contract.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    failures: list[dict] = []
    product_blockers: list[dict] = []
    checkpoint: dict = {}
    if not CHECKPOINT_PATH.exists():
        failures.append({"code": "CHECKPOINT_MISSING", "detail": str(CHECKPOINT_PATH)})
    else:
        checkpoint = load_json(CHECKPOINT_PATH)

    service_refresh = checkpoint.get("service_refresh") or {}
    evidence = checkpoint.get("evidence") or {}
    p0_status = checkpoint.get("p0_status") or {}
    round_005_status = checkpoint.get("round_005_status") or {}
    event_epoch = p0_status.get("event_epoch") or {}

    if checkpoint:
        if checkpoint.get("checkpoint") != "2026-06-21 21:22 CST P0 durable epoch_set validation":
            failures.append({"code": "CHECKPOINT_TITLE_MISMATCH", "detail": checkpoint.get("checkpoint")})
        if service_refresh.get("backend_health") != "ok":
            failures.append({"code": "BACKEND_HEALTH_NOT_OK", "detail": service_refresh.get("backend_health")})
        if service_refresh.get("frontend_http") != 200:
            failures.append({"code": "FRONTEND_HTTP_NOT_200", "detail": service_refresh.get("frontend_http")})
        for key in ["p0_runner", "p0_acceptance", "professional_chinese_gate", "round_005", "report_zip", "trace_zip"]:
            if not str(evidence.get(key, "")).strip():
                failures.append({"code": "CHECKPOINT_EVIDENCE_MISSING", "detail": key})
        if p0_status.get("runner_verdict") != "pass":
            failures.append({"code": "RUNNER_VERDICT_NOT_PASS", "detail": p0_status.get("runner_verdict")})
        if p0_status.get("acceptance_status") != "passed":
            failures.append({"code": "P0_ACCEPTANCE_NOT_PASSED", "detail": p0_status.get("acceptance_status")})
        if p0_status.get("product_gate_status") != "not_blocked_by_this_contract":
            failures.append({"code": "P0_PRODUCT_GATE_STATUS_UNEXPECTED", "detail": p0_status.get("product_gate_status")})
        if event_epoch.get("status") != "persistent_epoch_set_created":
            failures.append({"code": "EPOCH_STATUS_NOT_PERSISTENT", "detail": event_epoch.get("status")})
        if not event_epoch.get("epoch_set_id"):
            failures.append({"code": "EPOCH_SET_ID_MISSING", "detail": event_epoch})
        if not isinstance(event_epoch.get("epoch_set_revision"), int):
            failures.append({"code": "EPOCH_REVISION_INVALID", "detail": event_epoch.get("epoch_set_revision")})
        if round_005_status.get("status") != "completed":
            failures.append({"code": "ROUND_005_NOT_COMPLETED", "detail": round_005_status.get("status")})

    output = {
        "schema_version": "qlanalyser-p0-gap-repair-acceptance-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not failures else "failed",
        "repair_slice_status": "passed" if not failures else "failed",
        "product_gate_status": "blocked" if product_blockers else "not_blocked_by_this_contract",
        "important_boundary": "This validates the P0 durable checkpoint slice evidence. It is not P0 stable promotion, product release pass, or VR-EO pass.",
        "checkpoint_path": str(CHECKPOINT_PATH),
        "failures": failures,
        "warnings": [],
        "product_blockers": product_blockers,
        "checks": {
            "service_refresh": service_refresh,
            "event_epoch": event_epoch,
            "round_005_status": round_005_status,
            "inherited_round_005_blockers": round_005_status.get("blockers", []) if checkpoint else [],
            "evidence_paths": evidence,
        },
        "what_07_can_consume_next": [
            "Use the durable epoch_set checkpoint as the current P0 handoff basis.",
            "Treat round_005 QC/bad-channel blockers as the next product work slice.",
            "Keep the gap-repair slice separate from stable promotion or release-pass claims.",
        ],
        "07A_SHORT_PACKET_METRICS": {
            "mini/script packet count": 1,
            "script packet used": "p0 durable epoch-set checkpoint consumer",
            "GPT-5.5 low-value work avoided": "file existence checks, JSON field validation, checkpoint path wiring",
            "concurrency frontier": "single checkpoint consumer over durable epoch-set and round_005 status",
            "long-term platform asset produced": "runnable P0 gap-repair checkpoint consumer",
            "owner boundary respected": "yes",
            "handoff target": "07 main owner",
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
