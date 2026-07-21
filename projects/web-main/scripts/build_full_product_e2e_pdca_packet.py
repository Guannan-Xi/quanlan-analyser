from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "work" / "release_evidence" / "07-full-product-e2e-pdca"

DOCS = [
    "docs/product/qlanalyser_full_product_e2e_requirements_20260626.md",
    "docs/product/qlanalyser_full_product_e2e_design_20260626.md",
    "docs/product/qlanalyser_full_product_e2e_test_plan_20260626.md",
    "docs/product/qlanalyser_full_product_e2e_execution_packet_20260626.md",
]

METHOD_EXPECTATIONS = [
    {
        "method_id": "qc_data_preparation",
        "ui_actions": ["data row auto-preview", "bad channel restore", "segment restore", "event label restore"],
        "backend_module": "qc",
        "workflow_id": "metadata_qc",
        "source_files": [
            "eeg_core/preprocess/qc_preview.py",
            "eeg_core/preprocess/quality.py",
            "backend/services/data_preparation_service.py",
        ],
        "runner_functions": ["run_qc_preview", "run_quality_check"],
        "reference_check": "MNE raw metadata/channel/event preview, non-destructive preparation edits",
    },
    {
        "method_id": "psd",
        "ui_actions": ["run-psd"],
        "backend_module": "psd",
        "workflow_id": "resting_psd",
        "source_files": ["eeg_core/analysis/psd.py"],
        "runner_functions": ["run_psd"],
        "reference_check": "MNE/NumPy spectral estimate behavior, frequency range, bandpower outputs",
    },
    {
        "method_id": "erp",
        "ui_actions": ["run-erp"],
        "backend_module": "erp",
        "workflow_id": "erp_p300",
        "source_files": ["eeg_core/analysis/erp.py"],
        "runner_functions": ["run_erp"],
        "reference_check": "event epoching, baseline window, latency/amplitude recovery",
    },
    {
        "method_id": "tfr",
        "ui_actions": ["run-tfr"],
        "backend_module": "tfr",
        "workflow_id": "tfr_ersp_itc",
        "source_files": ["eeg_core/analysis/tfr.py"],
        "runner_functions": ["run_tfr"],
        "reference_check": "time-frequency power/ITC shape, event lock, baseline interpretation",
    },
    {
        "method_id": "multitaper_psd",
        "ui_actions": ["run-multitaper-psd"],
        "backend_module": "multitaper_psd_tfr",
        "workflow_id": "multitaper_psd_tfr",
        "source_files": ["eeg_core/analysis/multitaper_psd_tfr.py"],
        "runner_functions": ["run_multitaper_psd_tfr"],
        "reference_check": "multitaper PSD family behavior and output family separation",
    },
    {
        "method_id": "multitaper_tfr",
        "ui_actions": ["run-multitaper-tfr"],
        "backend_module": "multitaper_psd_tfr",
        "workflow_id": "multitaper_psd_tfr",
        "source_files": ["eeg_core/analysis/multitaper_psd_tfr.py"],
        "runner_functions": ["run_multitaper_psd_tfr"],
        "reference_check": "multitaper TFR family behavior and output family separation",
    },
    {
        "method_id": "reference_csd",
        "ui_actions": ["run-reference-csd"],
        "backend_module": "reference_csd",
        "workflow_id": "reference_csd",
        "source_files": ["eeg_core/analysis/reference_csd.py"],
        "runner_functions": ["run_reference_csd"],
        "reference_check": "reference transform before/after, CSD/reference boundary",
    },
    {
        "method_id": "pac",
        "ui_actions": ["run-pac"],
        "backend_module": "pac",
        "workflow_id": "pac_cfc",
        "source_files": ["eeg_core/analysis/pac.py"],
        "runner_functions": ["run_pac"],
        "reference_check": "phase-amplitude coupling descriptor, surrogate/null boundary if available",
    },
    {
        "method_id": "connectivity",
        "ui_actions": ["run-connectivity"],
        "backend_module": "connectivity",
        "workflow_id": "connectivity",
        "source_files": ["eeg_core/analysis/connectivity.py"],
        "runner_functions": ["run_connectivity"],
        "reference_check": "correlation/coherence matrix, sensor-space association boundary",
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_status_for(path: str) -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--", path],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return result.stdout.strip() or "clean_or_tracked_unchanged"


def build_docs_status() -> list[dict[str, Any]]:
    rows = []
    for item in DOCS:
        path = ROOT / item
        rows.append(
            {
                "path": item,
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else None,
                "sha256": sha256_file(path),
                "git_status": git_status_for(item),
            }
        )
    return rows


def inventory_pages() -> list[dict[str, Any]]:
    pages = []
    html_paths = sorted((ROOT / "frontend").glob("*.html")) + sorted((ROOT / "frontend" / "research-module").glob("*.html"))
    for path in html_paths:
        text = path.read_text(encoding="utf-8")
        title = (re.search(r"<title>([^<]*)</title>", text, flags=re.I) or [None, ""])[1]
        ids = re.findall(r'id="([^"]+)"', text)
        data_actions = re.findall(r'data-(?:real-action|action|module|route|page)="([^"]*)"', text)
        body_len = len(text)
        risk = "high" if path.name in {"index.html", "module-lab.html", "qc-lab.html"} or "research-module" in rel(path) else "medium"
        pages.append(
            {
                "path": rel(path),
                "title": title,
                "ids_sample": ids[:30],
                "data_actions_sample": data_actions[:40],
                "body_bytes": body_len,
                "scroll_risk": risk,
                "required_viewports": ["desktop-1440x1000", "laptop-1280x800", "mobile-390x844", "wide-1920x1080"],
                "required_scroll_states": ["top", "middle", "bottom"] if risk == "high" else ["top", "bottom"],
            }
        )
    return pages


def inventory_backend_routes() -> list[dict[str, Any]]:
    routes = []
    for path in sorted((ROOT / "backend" / "api").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(
            r'@router\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\'][\s\S]*?\n(?:async\s+)?def\s+([a-zA-Z0-9_]+)',
            text,
        ):
            method, route, handler = match.groups()
            mutability = "read" if method == "get" else "write"
            routes.append(
                {
                    "file": rel(path),
                    "method": method.upper(),
                    "route": route,
                    "handler": handler,
                    "mutability": mutability,
                    "smoke_policy": "safe_get" if mutability == "read" else "fixture_payload_or_skip_with_reason",
                }
            )
    return routes


def _imports_and_functions(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    imports: list[str] = []
    functions: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {"parse_error": str(exc), "imports": [], "functions": []}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    return {"imports": sorted(set(imports)), "functions": sorted(functions)}


def workflow_templates() -> list[dict[str, Any]]:
    path = ROOT / "backend" / "services" / "task_service.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_BASE_WORKFLOW_TEMPLATES":
                    value = ast.literal_eval(node.value)
                    return value
    return []


def inventory_methods() -> dict[str, Any]:
    analysis_files = {}
    for path in sorted((ROOT / "eeg_core" / "analysis").glob("*.py")):
        analysis_files[rel(path)] = _imports_and_functions(path)
    for path in sorted((ROOT / "eeg_core" / "preprocess").glob("*.py")):
        analysis_files[rel(path)] = _imports_and_functions(path)

    workflows = workflow_templates()
    workflow_by_id = {item.get("id"): item for item in workflows}
    method_rows = []
    for expected in METHOD_EXPECTATIONS:
        source_status = []
        for source in expected["source_files"]:
            p = ROOT / source
            funcs = analysis_files.get(source, {}).get("functions", [])
            source_status.append(
                {
                    "path": source,
                    "exists": p.exists(),
                    "sha256": sha256_file(p),
                    "runner_functions_found": [fn for fn in expected["runner_functions"] if fn in funcs],
                    "all_functions_sample": funcs[:30],
                }
            )
        workflow = workflow_by_id.get(expected["workflow_id"])
        method_rows.append(
            {
                **expected,
                "source_status": source_status,
                "workflow_contract": workflow,
                "contract_found": workflow is not None,
            }
        )
    return {
        "analysis_files": analysis_files,
        "workflow_templates": workflows,
        "methods": method_rows,
    }


def build_deepseek_prompt(paths: dict[str, str]) -> str:
    return f"""# DeepSeek Researcher Workflow Logic Review Packet

Role: Chinese logic and researcher-workflow reviewer.

Important boundary:
- You are not the release owner.
- Do not claim final pass/fail.
- Review whether the workflow, wording, and operation order match EEG researchers' habits.
- Focus on user logic, prerequisites, recoverability, and Chinese copy clarity.
- Do not invent product features not present in the documents.

Inputs:
- Requirements: {paths['requirements']}
- Design: {paths['design']}
- Test plan: {paths['test_plan']}
- Page inventory: {paths['page_inventory']}
- Backend route inventory: {paths['backend_inventory']}
- Method source inventory: {paths['method_inventory']}

Please return a compact Markdown review with this structure:

```text
status: success|partial|blocked
route_note: official DeepSeek direct route, no Headroom
researcher_workflow_findings:
- severity: P0|P1|P2|P3
  requirement_id:
  issue:
  why_it_matters_for_researchers:
  recommended_change:
copy_or_logic_findings:
- severity:
  surface_or_doc:
  issue:
  recommended_wording_or_logic:
questions_for_codex_final_acceptance:
- ...
do_not_overclaim:
- ...
```
"""


def main() -> int:
    (EVIDENCE_ROOT / "00_docs").mkdir(parents=True, exist_ok=True)
    docs_status = build_docs_status()
    page_inventory = inventory_pages()
    backend_inventory = inventory_backend_routes()
    method_inventory = inventory_methods()

    docs_path = EVIDENCE_ROOT / "00_docs" / "docs_status.json"
    page_path = EVIDENCE_ROOT / "01_inventory" / "page_surface_inventory.json"
    backend_path = EVIDENCE_ROOT / "01_inventory" / "backend_api_inventory.json"
    method_path = EVIDENCE_ROOT / "01_inventory" / "analysis_method_inventory.json"

    write_json(docs_path, {"generated_at": now_iso(), "docs": docs_status})
    write_json(page_path, {"generated_at": now_iso(), "pages": page_inventory})
    write_json(backend_path, {"generated_at": now_iso(), "routes": backend_inventory, "route_count": len(backend_inventory)})
    write_json(method_path, {"generated_at": now_iso(), **method_inventory})

    prompt_paths = {
        "requirements": DOCS[0],
        "design": DOCS[1],
        "test_plan": DOCS[2],
        "page_inventory": rel(page_path),
        "backend_inventory": rel(backend_path),
        "method_inventory": rel(method_path),
    }
    deepseek_prompt_path = EVIDENCE_ROOT / "09_deepseek" / "researcher_logic_review_prompt.md"
    deepseek_prompt_path.parent.mkdir(parents=True, exist_ok=True)
    deepseek_prompt_path.write_text(build_deepseek_prompt(prompt_paths), encoding="utf-8")

    manifest = {
        "status": "prepared",
        "generated_at": now_iso(),
        "requirements": DOCS[0],
        "design": DOCS[1],
        "test_plan": DOCS[2],
        "evidence_root": rel(EVIDENCE_ROOT),
        "artifacts": {
            "docs_status": rel(docs_path),
            "page_inventory": rel(page_path),
            "backend_api_inventory": rel(backend_path),
            "analysis_method_inventory": rel(method_path),
            "deepseek_prompt": rel(deepseek_prompt_path),
        },
        "summary": {
            "docs_count": len(docs_status),
            "page_count": len(page_inventory),
            "backend_route_count": len(backend_inventory),
            "method_count": len(method_inventory["methods"]),
        },
        "next_commands": [
            "python -X utf8 scripts/check_no_mojibake.py docs/product/qlanalyser_full_product_e2e_requirements_20260626.md docs/product/qlanalyser_full_product_e2e_design_20260626.md docs/product/qlanalyser_full_product_e2e_test_plan_20260626.md",
            "python C:/Users/XGN/.codex/scripts/model-consultant.py --role polish --route-check",
            "python C:/Users/XGN/.codex/scripts/model-consultant.py --role polish --prompt work/release_evidence/07-full-product-e2e-pdca/09_deepseek/researcher_logic_review_prompt.md --output-file work/release_evidence/07-full-product-e2e-pdca/09_deepseek/researcher_logic_review.md --max-tokens 2400",
            "python -X utf8 scripts/check_running_backend_contract.py --base-url http://127.0.0.1:8001/api --evidence-dir work/release_evidence/07-full-product-e2e-pdca/04_backend_api",
            "python -X utf8 scripts/run_full_product_backend_api_smoke.py",
            "node scripts/acceptance_product_wide_ux_copy_governance.mjs",
        ],
    }
    manifest_path = EVIDENCE_ROOT / "full_product_e2e_pdca_manifest.json"
    write_json(manifest_path, manifest)
    print(json.dumps({"status": "prepared", "manifest": str(manifest_path), "summary": manifest["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
