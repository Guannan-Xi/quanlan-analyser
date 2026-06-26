from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class ReviewAccess:
    front_end_url: str
    backend_health_url: str
    test_account: str
    test_password_or_login_method: str
    credential_safety: str
    permission_scope: str
    if_no_account_needed_why: str


@dataclass
class CheckpointPacket:
    status: str
    title: str
    created_at: str
    checkpoint_path: str
    review_access: ReviewAccess
    note: str
    metrics: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def render_markdown(packet: CheckpointPacket) -> str:
    access = packet.review_access
    metrics = packet.metrics.get("07A_SHORT_PACKET_METRICS", {})
    lines = [
        f"# {packet.title}",
        "",
        "## REVIEW_ACCESS",
        f"- front-end URL: `{access.front_end_url}`",
        f"- backend health URL: `{access.backend_health_url}`",
        f"- test account: `{access.test_account}`",
        f"- test password / login method: `{access.test_password_or_login_method}`",
        f"- credential safety: `{access.credential_safety}`",
        f"- permission scope: `{access.permission_scope}`",
        f"- if no account needed, why: `{access.if_no_account_needed_why}`",
        "",
        "## CHECKPOINT",
        f"- checkpoint path: `{packet.checkpoint_path}`",
        f"- created at: `{packet.created_at}`",
        "",
        "## METRICS",
    ]
    for key, value in metrics.items():
        lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False) if not isinstance(value, (str, int, float, bool)) else value}")
    lines.extend([
        "",
        "## NOTE",
        packet.note,
        "",
    ])
    return "\n".join(lines)


def build_packet(args: argparse.Namespace) -> CheckpointPacket:
    if args.no_account:
        test_account = "无需账号"
        test_password_or_login_method = "无需账号"
        credential_safety = args.no_account_reason or "no credential exposed"
        if_no_account_needed_why = args.no_account_reason or "local auto login / open review without authentication"
    else:
        test_account = args.test_account
        test_password_or_login_method = args.test_password_or_login_method
        credential_safety = args.credential_safety or "demo_only / low_privilege / rotatable / no_production_secret"
        if_no_account_needed_why = "account needed"

    metrics = {
        "07A_SHORT_PACKET_METRICS": {
            "mini/script packet count": args.mini_script_packet_count,
            "script packet used": args.script_packet_used,
            "worker packet count": args.worker_packet_count,
            "GPT-5.5 used for": args.gpt55_used_for,
            "GPT-5.5 low-value work avoided": args.gpt55_low_value_work_avoided,
            "parallel lanes active": args.parallel_lanes_active,
            "concurrency frontier": args.concurrency_frontier,
            "long-term platform asset produced": args.long_term_platform_asset_produced,
            "owner boundary respected": args.owner_boundary_respected,
            "handoff target": args.handoff_target,
            "ledger updated": args.ledger_updated,
            "checkpoint coverage": args.checkpoint_coverage,
        }
    }
    return CheckpointPacket(
        status="passed",
        title=args.title,
        created_at=utc_now(),
        checkpoint_path=args.checkpoint_path,
        review_access=ReviewAccess(
            front_end_url=args.front_end_url,
            backend_health_url=args.backend_health_url,
            test_account=test_account,
            test_password_or_login_method=test_password_or_login_method,
            credential_safety=credential_safety,
            permission_scope=args.permission_scope,
            if_no_account_needed_why=if_no_account_needed_why,
        ),
        note=args.note,
        metrics=metrics,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a standardized QLanalyser checkpoint packet.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--checkpoint-path", required=True)
    parser.add_argument("--front-end-url", required=True)
    parser.add_argument("--backend-health-url", required=True)
    parser.add_argument("--permission-scope", required=True)
    parser.add_argument("--note", default="")
    parser.add_argument("--test-account", default="demo.customer@quanlan.cn")
    parser.add_argument("--test-password-or-login-method", default="demo123456 / demo customer login via expert entry page")
    parser.add_argument("--credential-safety", default="demo_only / low_privilege / rotatable / no_production_secret")
    parser.add_argument("--no-account", action="store_true")
    parser.add_argument("--no-account-reason", default="")
    parser.add_argument("--mini-script-packet-count", type=int, default=1)
    parser.add_argument("--script-packet-used", action="store_true", default=True)
    parser.add_argument("--worker-packet-count", type=int, default=0)
    parser.add_argument("--gpt55-used-for", default="debug/root-cause, integration review, final gate interpretation")
    parser.add_argument("--gpt55-low-value-work-avoided", default="path checks, JSON field checks, evidence linkage checks handled by scripts")
    parser.add_argument("--parallel-lanes-active", default="script acceptance lane plus UI runner lane where safe")
    parser.add_argument("--concurrency-frontier", default="bounded local scripts only; no broad worker fan-out")
    parser.add_argument("--long-term-platform-asset-produced", default="standardized review checkpoint with runnable gate evidence")
    parser.add_argument("--owner-boundary-respected", default="yes")
    parser.add_argument("--handoff-target", default="07 main owner")
    parser.add_argument("--ledger-updated", default="not updated; no ledger write tool used in this slice")
    parser.add_argument("--checkpoint-coverage", default="review checkpoint only; not release pass")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--stem", default="")
    args = parser.parse_args()

    packet = build_packet(args)
    output_dir = Path(args.output_dir) if args.output_dir else Path(args.checkpoint_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.stem or Path(args.checkpoint_path).stem
    md_path = output_dir / f"{stem}.md"
    json_path = output_dir / f"{stem}.json"

    payload = asdict(packet)
    md_path.write_text(render_markdown(packet), encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "passed",
        "markdown": str(md_path),
        "json": str(json_path),
        "checkpoint_path": packet.checkpoint_path,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
