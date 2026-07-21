from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FIELDS = (
    ("front_end_url", "front-end URL"),
    ("backend_health_url", "backend health URL"),
    ("test_account", "test account"),
    ("test_password_or_login_method", "test password / login method"),
    ("credential_safety", "credential safety"),
    ("permission_scope", "permission scope"),
    ("if_no_account_needed_why", "if no account needed, why"),
)


def get_alias(payload: dict[str, Any], canonical: str, legacy: str) -> Any:
    return payload.get(canonical, payload.get(legacy))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def declares_no_account(*values: str) -> bool:
    text = " ".join(str(value).lower() for value in values)
    return any(
        token in text
        for token in (
            "无需账号",
            "无需登录",
            "no account",
            "no login",
            "not required",
            "not needed",
        )
    )


def validate_payload(payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    access = payload.get("review_access") or payload.get("REVIEW_ACCESS") or {}

    if not isinstance(access, dict):
        return ["review_access section missing or invalid"]

    for canonical, legacy in REQUIRED_FIELDS:
        value = get_alias(access, canonical, legacy)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"missing or empty field: {canonical}")

    test_account = get_alias(access, "test_account", "test account") or ""
    login_method = get_alias(access, "test_password_or_login_method", "test password / login method") or ""
    credential_safety = get_alias(access, "credential_safety", "credential safety") or ""
    no_account_reason = get_alias(access, "if_no_account_needed_why", "if no account needed, why") or ""

    if declares_no_account(str(test_account), str(login_method), str(no_account_reason)):
        if not no_account_reason.strip():
            failures.append("no-account flow declared but no reason given")
    else:
        if "account needed" not in str(no_account_reason).lower() and "需要" not in str(no_account_reason):
            failures.append("account-based checkpoint should state why account is needed")

    if not any(token in str(credential_safety).lower() for token in ("demo_only", "low_privilege", "rotatable", "no_production_secret")):
        failures.append("credential safety should state demo_only / low_privilege / rotatable / no_production_secret or equivalent")

    return failures


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python scripts/acceptance_checkpoint_packet_access.py <checkpoint_packet_json>", file=sys.stderr)
        return 2

    path = Path(args[0])
    if not path.exists():
        result = {
            "status": "failed",
            "path": str(path),
            "failures": ["json file not found"],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    payload = load_json(path)
    failures = validate_payload(payload)
    result = {
        "status": "passed" if not failures else "failed",
        "path": str(path),
        "failures": failures,
        "review_access": payload.get("review_access") or payload.get("REVIEW_ACCESS"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
