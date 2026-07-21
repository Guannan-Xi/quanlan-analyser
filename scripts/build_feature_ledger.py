from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs" / "workspace-inventory"

MODULE_RULES = [
    ("platform.accounts", ("backend/api/accounts.py", "backend/services/account_service.py")),
    ("platform.projects", ("backend/api/projects.py", "backend/models/project.py")),
    ("platform.subjects", ("backend/api/subjects.py", "backend/models/subject.py")),
    ("platform.eeg-files", ("backend/api/eeg_files.py", "backend/models/eeg_file.py")),
    ("platform.templates", ("backend/api/templates.py",)),
    ("platform.tasks", ("backend/api/tasks.py", "backend/services/task_service.py", "backend/models/analysis_task.py")),
    ("platform.artifacts", ("backend/api/artifacts.py", "backend/models/artifact.py")),
    ("platform.reports", ("backend/api/reports.py", "backend/services/report_service.py", "backend/models/report.py", "eeg_core/report/", "worker/tasks/report.py")),
    ("platform.billing", ("backend/api/billing.py", "backend/services/billing_service.py", "backend/services/invoice_service.py", "backend/services/quota_service.py")),
    ("platform.admin", ("backend/api/admin.py",)),
    ("platform.storage", ("backend/services/storage_service.py", "backend/services/object_storage_service.py", "backend/services/state_store.py")),
    ("platform.delivery", ("backend/services/customer_delivery_service.py",)),
    ("platform.governance", ("backend/services/audit_service.py", "backend/services/readiness_service.py", "backend/services/backup_service.py", "backend/models/governance.py")),
    ("platform.workflow", ("backend/api/workflow.py", "eeg_core/workflow/")),
    ("feature.data-preparation", ("backend/api/data_preparation.py", "backend/services/data_preparation_service.py", "backend/models/data_preparation.py")),
    ("feature.waveform-workbench", ("waveform-workbench", "waveform_chunk_service.py")),
    ("feature.qc", ("qc_preview.py", "quality.py", "qc-lab", "lab_edf_reviewer")),
    ("feature.psd", ("analysis/psd.py", "worker/tasks/psd.py", "research-module/psd", "research-modules/psd")),
    ("feature.band-power", ("analysis/band_power.py",)),
    ("feature.erp", ("analysis/erp.py", "worker/tasks/erp.py", "research-module/erp", "research-modules/erp")),
    ("feature.tfr", ("analysis/tfr.py", "analysis/time_frequency.py", "research-module/tfr", "research-modules/tfr")),
    ("feature.multitaper", ("analysis/multitaper_psd_tfr.py",)),
    ("feature.pac-v2", ("analysis/pac_v2.py",)),
    ("feature.pac-v1", ("analysis/pac.py", "research-module/pac", "research-modules/pac")),
    ("feature.connectivity", ("analysis/connectivity.py", "research-module/connectivity", "research-modules/connectivity")),
    ("feature.reference-csd", ("analysis/reference_csd.py", "source_localization")),
    ("feature.epilepsy-ml", ("epilepsy_ml", "newEpilepsy")),
    ("feature.epilepsy", ("epilepsy",)),
    ("lab.module-lab", ("module-lab", "research-modules.html", "research-modules.js")),
    ("lab.demo", ("lab_demo", "standalone-lab", "expert-entry-demo", "open-design-entry-demo", "staging-subview", "preview")),
    ("platform.frontend-shell", ("frontend/index.html", "frontend/app.js", "frontend/styles.css")),
    ("platform.deployment", ("deploy/", "docker", "requirements.txt")),
    ("platform.scripts-acceptance", ("scripts/",)),
    ("research.qeeg-64ch", ("projects/qeeg-64ch-research/",)),
    ("research.spike-analysis", ("projects/spike-analysis/",)),
]


def load_csv(name: str) -> list[dict[str, str]]:
    with (INVENTORY / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, object]], fields: list[str]) -> None:
    with (INVENTORY / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def module_for(path: str) -> str:
    normalized = path.replace("\\", "/")
    for module_id, needles in MODULE_RULES:
        if any(needle in normalized for needle in needles):
            return module_id
    if normalized.startswith("projects/web-main/backend/models/"):
        return "platform.models"
    if normalized.startswith("projects/web-main/backend/services/"):
        return "platform.services-other"
    if normalized.startswith("projects/web-main/backend/api/"):
        return "platform.api-other"
    if normalized.startswith("projects/web-main/worker/"):
        return "platform.worker-other"
    if normalized.startswith("projects/web-main/eeg_core/io/"):
        return "shared.eeg-io"
    if normalized.startswith("projects/web-main/eeg_core/preprocess/"):
        return "shared.preprocessing"
    if normalized.startswith("projects/web-main/eeg_core/stats/"):
        return "feature.statistics"
    if normalized.startswith("projects/web-main/eeg_core/analysis/"):
        return "feature.analysis-other"
    if normalized.startswith("projects/web-main/frontend/assets/"):
        return "assets.static-evidence"
    if normalized.startswith("projects/web-main/frontend/"):
        return "platform.frontend-support"
    if normalized.startswith("projects/web-main/docs/"):
        return "governance.web-docs"
    if normalized.startswith("projects/web-main/"):
        return "platform.web-support"
    return "unclassified"


def layer_for(path: str) -> str:
    if "/frontend/" in path:
        return "frontend"
    if "/backend/api/" in path:
        return "api"
    if "/backend/services/" in path:
        return "service"
    if "/backend/models/" in path:
        return "model-contract"
    if "/worker/" in path:
        return "worker"
    if "/eeg_core/" in path or "/src/qlanalyser_eeg64/" in path:
        return "domain"
    if "/tests/" in path or "/scripts/" in path:
        return "test-or-tooling"
    if "/docs/" in path or path.endswith("README.md"):
        return "documentation"
    return "support"


def state_for(module_id: str, path: str) -> str:
    if module_id == "research.spike-analysis":
        return "placeholder"
    if module_id == "research.qeeg-64ch":
        return "frozen-at-6b18faf"
    if module_id.startswith("lab."):
        return "lab-or-demo"
    if module_id.startswith("assets."):
        return "static-evidence-or-asset"
    if ".bak" in path or "legacy" in path.lower():
        return "historical-candidate"
    return "implemented-or-supporting"


def build_file_ledger(files: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for item in files:
        module_id = module_for(item["path"])
        rows.append(
            {
                "feature_id": f"file:{item['path']}",
                "module_id": module_id,
                "project": item["project"],
                "layer": layer_for(item["path"]),
                "state": state_for(module_id, item["path"]),
                "source_path": item["path"],
                "source_symbol": "",
                "evidence": f"sha256:{item['sha256']}",
                "notes": "file-level coverage; does not imply behavioral validation",
            }
        )
    return rows


def build_symbol_ledger(symbols: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for item in symbols:
        if item["kind"] not in {"api-route", "router-registration"}:
            continue
        module_id = module_for(item["path"])
        rows.append(
            {
                "feature_id": f"{item['kind']}:{item['path']}:{item['line']}:{item['symbol']}",
                "module_id": module_id,
                "project": item["project"],
                "layer": "api" if item["kind"] == "api-route" else "api-registration",
                "state": state_for(module_id, item["path"]),
                "source_path": item["path"],
                "source_symbol": item["symbol"],
                "evidence": item["detail"],
                "notes": "AST-discovered route/registration",
            }
        )
    return rows


def build_frontend_ledger(entries: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for item in entries:
        module_id = module_for(item["path"])
        rows.append(
            {
                "feature_id": f"frontend-entry:{item['path']}",
                "module_id": module_id,
                "project": "web-main",
                "layer": "frontend-entry",
                "state": state_for(module_id, item["path"]),
                "source_path": item["path"],
                "source_symbol": "",
                "evidence": f"lines={item['line_count']};api_calls={item['api_calls']};events={item['event_listener_count']}",
                "notes": "frontend entry coverage; dynamic API paths require module-level review",
            }
        )
    return rows


def build_traceability(ledger: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    states: dict[str, set[str]] = defaultdict(set)
    for row in ledger:
        module_id = str(row["module_id"])
        grouped[module_id][str(row["layer"])].append(str(row["source_path"]))
        states[module_id].add(str(row["state"]))
    rows = []
    for module_id in sorted(grouped):
        layers = grouped[module_id]
        rows.append(
            {
                "module_id": module_id,
                "states": ";".join(sorted(states[module_id])),
                "frontend": " | ".join(sorted(set(layers.get("frontend", []) + layers.get("frontend-entry", [])))),
                "api": " | ".join(sorted(set(layers.get("api", []) + layers.get("api-registration", [])))),
                "service": " | ".join(sorted(set(layers.get("service", [])))),
                "worker": " | ".join(sorted(set(layers.get("worker", [])))),
                "domain": " | ".join(sorted(set(layers.get("domain", [])))),
                "report": "",
                "tests_evidence": " | ".join(sorted(set(layers.get("test-or-tooling", [])))),
                "other_layers": ";".join(sorted(k for k in layers if k not in {"frontend", "frontend-entry", "api", "api-registration", "service", "worker", "domain", "test-or-tooling"})),
            }
        )
    return rows


def main() -> int:
    files = load_csv("files.csv")
    symbols = load_csv("python-symbols.csv")
    frontend = load_csv("frontend-entries.csv")
    ledger = build_file_ledger(files) + build_symbol_ledger(symbols) + build_frontend_ledger(frontend)
    ledger.sort(key=lambda row: str(row["feature_id"]))
    fields = ["feature_id", "module_id", "project", "layer", "state", "source_path", "source_symbol", "evidence", "notes"]
    write_csv("feature-ledger.csv", ledger, fields)
    traceability = build_traceability(ledger)
    write_csv(
        "traceability-matrix.csv",
        traceability,
        ["module_id", "states", "frontend", "api", "service", "worker", "domain", "report", "tests_evidence", "other_layers"],
    )
    module_counts = Counter(str(row["module_id"]) for row in ledger)
    summary = {
        "schema_version": "feature-ledger-v1",
        "stable_baseline_commit": "6b18faf",
        "file_records": len(files),
        "route_and_registration_records": sum(row["layer"] in {"api", "api-registration"} for row in ledger),
        "frontend_entry_records": len(frontend),
        "ledger_records": len(ledger),
        "module_count": len(module_counts),
        "unclassified_count": module_counts.get("unclassified", 0),
        "qeeg_status": "frozen-at-6b18faf; live post-baseline drift excluded",
        "module_counts": dict(sorted(module_counts.items())),
        "limitations": [
            "File coverage is exhaustive for the frozen inventory, but behavioral completeness still requires module-by-module review.",
            "Dynamic frontend API paths are not fully resolved by literal scanning.",
            "QEEG live changes after 6b18faf are intentionally excluded until the external writer stops.",
        ],
    }
    (INVENTORY / "feature-ledger-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ledger_records": len(ledger), "modules": len(module_counts), "unclassified": module_counts.get("unclassified", 0)}))
    return 1 if module_counts.get("unclassified", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
