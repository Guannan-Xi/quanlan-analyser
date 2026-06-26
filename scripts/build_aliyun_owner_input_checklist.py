from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREFLIGHT = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "aliyun_staging_preflight.json"
DEFAULT_OUTPUT = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "owner_input_checklist.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_values(check: dict[str, Any], key: str) -> list[str]:
    values = check.get(key) or []
    if isinstance(values, str):
        return [values]
    return [str(item) for item in values]


def render_check(check: dict[str, Any]) -> list[str]:
    lines = [
        f"### {check['name']}",
        "",
        f"- Status: `{check['status']}`",
        f"- Why it matters: {check.get('detail', '')}",
    ]
    for key in ("missing", "expected"):
        values = list_values(check, key)
        if values:
            lines.append(f"- {key}:")
            lines.extend([f"  - `{item}`" for item in values])
    for key in ("template", "path", "latest_path", "historical_path"):
        if check.get(key):
            lines.append(f"- {key}: `{check[key]}`")
    return lines + [""]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build owner-facing Aliyun/provider input checklist from strict preflight evidence.")
    parser.add_argument("--preflight", default=str(DEFAULT_PREFLIGHT), help="Preflight JSON path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Markdown checklist output path.")
    args = parser.parse_args()

    preflight_path = Path(args.preflight)
    output_path = Path(args.output)
    payload = load_json(preflight_path)
    todo_checks = [check for check in payload.get("checks", []) if check.get("status") == "todo"]
    failed_checks = [check for check in payload.get("checks", []) if check.get("status") == "fail"]

    lines = [
        "# QLanalyser V01 Owner Input Checklist",
        "",
        f"Generated: {utc_now()}",
        "",
        "This checklist is generated from the strict Aliyun staging preflight. It contains only items still needed before public staging or production readiness can be claimed.",
        "",
        f"- Preflight status: `{payload.get('status')}`",
        f"- Source: `{preflight_path}`",
        f"- Safe claim: {payload.get('safe_claim', '')}",
        "",
        "## Blocking Inputs",
        "",
    ]
    if not todo_checks and not failed_checks:
        lines.append("No todo or failed checks remain. Run the cloud acceptance commands in order.")
        lines.append("")
    for check in failed_checks + todo_checks:
        lines.extend(render_check(check))

    lines.extend([
        "## Commands After Inputs Are Set",
        "",
    ])
    for command in payload.get("next_commands", []):
        lines.append(f"```powershell\n{command}\n```")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "status": "passed",
        "output": str(output_path),
        "todo": len(todo_checks),
        "failed": len(failed_checks),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
