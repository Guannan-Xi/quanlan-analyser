from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_MARKERS = (
    "## REVIEW_ACCESS",
    "front-end URL:",
    "backend health URL:",
    "test account:",
    "test password / login method:",
    "credential safety:",
    "permission scope:",
    "if no account needed, why:",
    "checkpoint path:",
)

REQUIRED_JSON_FIELDS = (
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


def validate_md(text: str) -> list[str]:
    failures: list[str] = []
    for marker in REQUIRED_MARKERS:
        if marker not in text:
            failures.append(f"missing markdown marker: {marker}")
    return failures


def validate_json(payload: dict[str, Any], checkpoint_path_fallback: str | None = None) -> list[str]:
    failures: list[str] = []
    access = payload.get("review_access") or payload.get("REVIEW_ACCESS") or {}
    if not isinstance(access, dict):
        return ["review_access section missing or invalid"]

    for canonical, legacy in REQUIRED_JSON_FIELDS:
        value = get_alias(access, canonical, legacy)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"missing json key: {canonical}")

    checkpoint_path = payload.get("checkpoint_path") or payload.get("checkpoint_id") or checkpoint_path_fallback
    if not isinstance(checkpoint_path, str) or not checkpoint_path.strip():
        failures.append("missing checkpoint_path")

    credential_safety = get_alias(access, "credential_safety", "credential safety") or ""
    if not any(token in str(credential_safety).lower() for token in ("demo_only", "low_privilege", "rotatable", "no_production_secret")):
        failures.append("credential safety should mention demo_only / low_privilege / rotatable / no_production_secret or equivalent")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate checkpoint packet access fields in QLanalyser evidence packets.")
    parser.add_argument("packet", help="Path to a checkpoint .md or .json packet")
    args = parser.parse_args()

    path = Path(args.packet)
    if not path.exists():
        print(json.dumps({"status": "failed", "path": str(path), "failures": ["file not found"]}, ensure_ascii=False, indent=2))
        return 1

    if path.suffix.lower() == ".md":
        failures = validate_md(path.read_text(encoding="utf-8", errors="replace"))
    else:
        failures = validate_json(load_json(path), str(path))

    result = {
        "status": "passed" if not failures else "failed",
        "path": str(path),
        "failures": failures,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
