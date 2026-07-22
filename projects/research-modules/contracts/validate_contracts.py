"""Validate research-modules contracts.

Checks every ``*.schema.json`` is a well-formed JSON Schema (2020-12) and that
each ``*.example.json`` validates against the schema named by its
``schema_version`` / sibling file. Degrades to structural JSON checks when the
``jsonschema`` package is unavailable, so it never blocks on an env gap.

Exit code 0 on success, 1 on any failure. No network, no secrets.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

try:
    import jsonschema
    from jsonschema.validators import Draft202012Validator

    HAVE_JSONSCHEMA = True
except Exception:  # pragma: no cover - env gap, not a contract failure
    HAVE_JSONSCHEMA = False


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_registry() -> dict[str, dict]:
    """Map each schema $id to its parsed schema for cross-$ref resolution."""
    registry: dict[str, dict] = {}
    for schema_path in sorted(HERE.rglob("*.schema.json")):
        schema = load_json(schema_path)
        schema_id = schema.get("$id")
        if schema_id:
            registry[schema_id] = schema
    return registry


def main() -> int:
    schema_paths = sorted(HERE.rglob("*.schema.json"))
    example_paths = sorted(HERE.rglob("*.example.json"))
    failures: list[str] = []

    registry = build_registry()

    for schema_path in schema_paths:
        rel = schema_path.relative_to(HERE)
        try:
            schema = load_json(schema_path)
        except json.JSONDecodeError as exc:
            failures.append(f"{rel}: invalid JSON ({exc})")
            continue
        if "$id" not in schema or "title" not in schema:
            failures.append(f"{rel}: missing $id or title")
        if HAVE_JSONSCHEMA:
            try:
                Draft202012Validator.check_schema(schema)
            except jsonschema.exceptions.SchemaError as exc:
                failures.append(f"{rel}: not a valid JSON Schema ({exc.message})")

    for example_path in example_paths:
        rel = example_path.relative_to(HERE)
        try:
            example = load_json(example_path)
        except json.JSONDecodeError as exc:
            failures.append(f"{rel}: invalid JSON ({exc})")
            continue
        sibling = example_path.with_name(example_path.name.replace(".example.json", ".schema.json"))
        if not sibling.exists():
            failures.append(f"{rel}: no sibling schema {sibling.name}")
            continue
        if HAVE_JSONSCHEMA:
            schema = load_json(sibling)

            def _retrieve(uri: str):
                if uri in registry:
                    return jsonschema.Resource(contents=registry[uri], specification=jsonschema.Draft202012)
                raise jsonschema.exceptions.RefResolutionError(uri)

            try:
                ref_registry = jsonschema.Registry(retrieve=_retrieve)
                validator = Draft202012Validator(schema, registry=ref_registry)
                errors = sorted(validator.iter_errors(example), key=lambda e: e.path)
                for err in errors:
                    failures.append(f"{rel}: {err.message} (at {list(err.path)})")
            except Exception as exc:  # pragma: no cover
                failures.append(f"{rel}: validation error ({exc})")

    result = {
        "schemas": len(schema_paths),
        "examples": len(example_paths),
        "jsonschema_available": HAVE_JSONSCHEMA,
        "failures": len(failures),
    }
    print(json.dumps(result))
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
