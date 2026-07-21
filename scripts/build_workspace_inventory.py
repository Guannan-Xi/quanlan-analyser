from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "workspace-inventory"
PROJECTS = {
    "web-main": ROOT / "projects" / "web-main",
    "qeeg-64ch-research": ROOT / "projects" / "qeeg-64ch-research",
    "spike-analysis": ROOT / "projects" / "spike-analysis",
}
EXCLUDED_PROJECT = ROOT / "projects" / "pc-qlanalyser"
EXCLUDED_DIR_NAMES = {
    ".git",
    ".ai",
    ".idea",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "results",
    "work",
    "outputs",
    "data",
}
GENERATED_DIR_NAMES = {"results", "outputs", "work", "data"}
RAW_DATA_EXTENSIONS = {
    ".bdf",
    ".edf",
    ".fif",
    ".set",
    ".cnt",
    ".vhdr",
    ".vmrk",
    ".eeg",
    ".mat",
    ".npy",
    ".npz",
    ".db",
    ".sqlite",
    ".sqlite3",
}
SECRET_NAME_RE = re.compile(
    r"(^|[._-])(secret|token|password|credential|api[_-]?key|private[_-]?key|cookie)([._-]|$)",
    re.IGNORECASE,
)
ROUTE_DECORATOR_RE = re.compile(r"^(get|post|put|patch|delete|options|head)$", re.IGNORECASE)
JS_FETCH_RE = re.compile(r"(?:fetch|apiFetch|requestJson)\s*\(\s*([`\"'])(.+?)\1")


@dataclass(frozen=True)
class FileRecord:
    project: str
    path: str
    size_bytes: int
    sha256: str
    extension: str
    category: str


@dataclass(frozen=True)
class PythonSymbol:
    project: str
    path: str
    symbol: str
    kind: str
    line: int
    detail: str


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(path: Path) -> str:
    suffix = path.suffix.lower()
    parts = {part.lower() for part in path.parts}
    if parts & GENERATED_DIR_NAMES:
        return "generated-output"
    if suffix in RAW_DATA_EXTENSIONS:
        return "raw-or-runtime-data"
    if suffix in {".py", ".js", ".mjs", ".html", ".css"}:
        return "source"
    if suffix in {".md", ".rst", ".txt"}:
        return "documentation"
    if suffix in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}:
        return "configuration-or-contract"
    if suffix in {".png", ".svg", ".csv", ".tsv"}:
        return "static-evidence-or-asset"
    if suffix in {".pkl", ".nrm"}:
        return "large-model-or-normative-asset"
    return "other"


def iter_project_files(project_root: Path):
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(project_root).parts
        if any(part in EXCLUDED_DIR_NAMES for part in relative_parts):
            continue
        yield path


def inventory_files() -> list[FileRecord]:
    records: list[FileRecord] = []
    for project, root in PROJECTS.items():
        for path in iter_project_files(root):
            records.append(
                FileRecord(
                    project=project,
                    path=relative(path),
                    size_bytes=path.stat().st_size,
                    sha256=sha256_file(path),
                    extension=path.suffix.lower(),
                    category=classify(path),
                )
            )
    return sorted(records, key=lambda item: item.path)


def decorator_name(node: ast.expr) -> tuple[str, str] | None:
    call = node if isinstance(node, ast.Call) else None
    func = call.func if call else node
    if not isinstance(func, ast.Attribute) or not ROUTE_DECORATOR_RE.match(func.attr):
        return None
    owner = func.value.id if isinstance(func.value, ast.Name) else "router"
    route = ""
    if call and call.args and isinstance(call.args[0], ast.Constant):
        route = str(call.args[0].value)
    return f"{owner}.{func.attr}", route


def python_symbols() -> list[PythonSymbol]:
    symbols: list[PythonSymbol] = []
    for project, root in PROJECTS.items():
        for path in iter_project_files(root):
            if path.suffix != ".py":
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError):
                symbols.append(
                    PythonSymbol(project, relative(path), "<parse-error>", "parse-error", 0, "")
                )
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(
                        PythonSymbol(project, relative(path), node.name, "function", node.lineno, "")
                    )
                    for decorator in node.decorator_list:
                        route = decorator_name(decorator)
                        if route:
                            method, route_path = route
                            symbols.append(
                                PythonSymbol(
                                    project,
                                    relative(path),
                                    node.name,
                                    "api-route",
                                    node.lineno,
                                    f"{method.upper()} {route_path}",
                                )
                            )
                elif isinstance(node, ast.ClassDef):
                    symbols.append(
                        PythonSymbol(project, relative(path), node.name, "class", node.lineno, "")
                    )
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr == "include_router":
                        target = ast.unparse(node.args[0]) if node.args else ""
                        symbols.append(
                            PythonSymbol(
                                project,
                                relative(path),
                                target,
                                "router-registration",
                                node.lineno,
                                "",
                            )
                        )
    return sorted(symbols, key=lambda item: (item.path, item.line, item.kind))


def frontend_entries() -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    root = PROJECTS["web-main"] / "frontend"
    for path in iter_project_files(root):
        if path.suffix.lower() not in {".html", ".js", ".mjs", ".css"}:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        entries.append(
            {
                "path": relative(path),
                "kind": path.suffix.lower().lstrip("."),
                "line_count": text.count("\n") + 1,
                "api_calls": sorted({match.group(2) for match in JS_FETCH_RE.finditer(text)}),
                "function_count": len(re.findall(r"\bfunction\s+[A-Za-z_$][\w$]*|(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*(?:async\s*)?\(", text)),
                "event_listener_count": text.count("addEventListener("),
            }
        )
    return sorted(entries, key=lambda item: str(item["path"]))


def generated_output_index() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for project, root in PROJECTS.items():
        for generated_name in GENERATED_DIR_NAMES:
            generated_root = root / generated_name
            if not generated_root.exists():
                continue
            count = 0
            size = 0
            for path in generated_root.rglob("*"):
                if path.is_file():
                    count += 1
                    size += path.stat().st_size
            records.append(
                {
                    "project": project,
                    "path": relative(generated_root),
                    "file_count": count,
                    "size_bytes": size,
                    "sha256": "not-hashed-generated-output",
                }
            )
    return sorted(records, key=lambda item: str(item["path"]))


def large_excluded_assets() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in EXCLUDED_PROJECT.rglob("*"):
        if not path.is_file():
            continue
        if path.stat().st_size < 5 * 1024 * 1024 and path.suffix.lower() not in {
            ".dll",
            ".ipynb",
            ".nrm",
            ".parquet",
            ".pkl",
            ".sav",
        }:
            continue
        records.append(
            {
                "path": relative(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "reason": "pc-qlanalyser excluded from modularization; large binary inventoried only",
            }
        )
    return sorted(records, key=lambda item: int(item["size_bytes"]), reverse=True)


def security_path_findings(records: list[FileRecord]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for record in records:
        name = Path(record.path).name
        if SECRET_NAME_RE.search(name) or name.startswith(".env"):
            findings.append({"path": record.path, "finding": "secret-like filename; manual review required"})
        if any(part.lower().startswith(("customer", "patient", "participant")) for part in Path(record.path).parts):
            findings.append({"path": record.path, "finding": "customer/patient-like path; provenance review required"})
        if record.extension in RAW_DATA_EXTENSIONS:
            findings.append({"path": record.path, "finding": "raw/runtime data extension; must remain excluded"})
    return findings


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_summary(
    files: list[FileRecord],
    symbols: list[PythonSymbol],
    frontend: list[dict[str, object]],
    generated: list[dict[str, object]],
    large_assets: list[dict[str, object]],
    findings: list[dict[str, str]],
) -> None:
    project_counts = Counter(record.project for record in files)
    category_counts = Counter(record.category for record in files)
    symbol_counts = Counter(symbol.kind for symbol in symbols)
    summary = {
        "schema_version": "workspace-inventory-v1",
        "scope": list(PROJECTS),
        "excluded_from_modularization": ["pc-qlanalyser"],
        "file_count": len(files),
        "file_counts_by_project": dict(sorted(project_counts.items())),
        "file_counts_by_category": dict(sorted(category_counts.items())),
        "python_symbol_counts": dict(sorted(symbol_counts.items())),
        "frontend_entry_count": len(frontend),
        "generated_output_roots": generated,
        "large_excluded_asset_count": len(large_assets),
        "path_level_security_finding_count": len(findings),
        "limitations": [
            "Generated output payloads are indexed by root only and are not hashed file-by-file.",
            "Secret scanning in this script is path-based; a separate content-signature scan is required before commit.",
            "Inventory presence does not prove feature correctness, lifecycle, or release readiness.",
        ],
    }
    (OUTPUT_DIR / "inventory-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic workspace asset inventories.")
    parser.add_argument("--check", action="store_true", help="Rebuild and report counts; reserved for CI parity.")
    parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = inventory_files()
    symbols = python_symbols()
    frontend = frontend_entries()
    generated = generated_output_index()
    large_assets = large_excluded_assets()
    findings = security_path_findings(files)

    write_csv(OUTPUT_DIR / "files.csv", [asdict(record) for record in files])
    write_csv(OUTPUT_DIR / "python-symbols.csv", [asdict(symbol) for symbol in symbols])
    write_csv(OUTPUT_DIR / "frontend-entries.csv", frontend)
    write_csv(OUTPUT_DIR / "generated-output-index.csv", generated)
    write_csv(OUTPUT_DIR / "large-excluded-assets.csv", large_assets)
    write_csv(OUTPUT_DIR / "security-path-review.csv", findings)
    write_summary(files, symbols, frontend, generated, large_assets, findings)

    print(
        json.dumps(
            {
                "files": len(files),
                "python_symbols": len(symbols),
                "frontend_entries": len(frontend),
                "security_path_findings": len(findings),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
