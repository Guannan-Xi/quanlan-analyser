from pathlib import Path

from backend.services import report_service, state_store, storage_service, task_service

ROOT = Path(__file__).resolve().parents[2]


def _path_status(path: Path) -> dict:
    return {
        "path": str(path),
        "exists": path.exists(),
        "writable": path.exists() and path.is_dir(),
    }


def get_v01_readiness() -> dict:
    """Return a conservative launch-readiness snapshot for the V01 research release.

    This is not a replacement for monitoring or a multi-user production database.
    It is a machine-readable contract that frontend, acceptance tests, and operators
    can use to verify that every V01 architectural layer is present and honest.
    """
    templates = task_service.WORKFLOW_TEMPLATES
    enabled = [item for item in templates if item.get("outputs")]
    disabled = [item for item in templates if not item.get("outputs")]
    storage_roots = {
        "uploads": _path_status(storage_service.UPLOAD_ROOT),
        "derivatives": _path_status(task_service.DERIVATIVES_ROOT),
        "reports": _path_status(report_service.REPORT_ROOT),
        "state": state_store.get_state_status(),
    }
    layers = [
        {
            "key": "frontend",
            "name": "Chinese V01 product workbench",
            "status": "ready",
            "evidence": ["flow navigation", "method workflow cards", "runtime API panel", "disabled advanced-method boundary"],
        },
        {
            "key": "api",
            "name": "FastAPI V01 surface",
            "status": "ready",
            "evidence": ["health", "projects", "eeg upload/metadata", "tasks", "artifacts", "reports", "billing-disabled honesty", "admin dashboard"],
        },
        {
            "key": "services",
            "name": "Service layer boundaries",
            "status": "ready",
            "evidence": ["storage_service", "metadata_service", "task_service", "report_service", "readiness_service", "JSON state registry"],
        },
        {
            "key": "worker_core",
            "name": "Worker/Core analysis path",
            "status": "ready",
            "evidence": ["QC", "Welch PSD", "ERP/P300 from annotations", "worker wrappers call eeg_core"],
        },
        {
            "key": "reports",
            "name": "Reproducible reports and artifacts",
            "status": "ready",
            "evidence": ["HTML", "ZIP", "tables", "reproducibility parameters/method/software/workflow"],
        },
        {
            "key": "operations",
            "name": "Launch operations boundary",
            "status": "ready_with_v01_limits",
            "evidence": ["acceptance scripts", "persistent JSON registry", "static deploy package", "public DOM/UI checks", "no formal billing or diagnosis"],
        },
    ]
    blockers = []
    for name, status in storage_roots.items():
        if not status["exists"]:
            blockers.append(f"missing storage root: {name}")
        if name == "state" and not status.get("writable"):
            blockers.append("state registry is not writable")
    return {
        "status": "ready" if not blockers else "blocked",
        "scope": "eeg-v01-production",
        "version": "0.1.0",
        "architecture_layers": layers,
        "enabled_workflows": [item["id"] for item in enabled],
        "disabled_workflows": [item["id"] for item in disabled],
        "storage_roots": storage_roots,
        "known_v01_limits": [
            "single-subject research workflow",
            "lightweight JSON registry; database-backed multi-user state is a V1.x hardening item",
            "no clinical diagnosis",
            "no AI interpretation",
            "no formal payment charging",
            "no external share links",
            "TFR/PAC/Connectivity disabled until scientific prerequisites are implemented",
        ],
        "blockers": blockers,
    }
