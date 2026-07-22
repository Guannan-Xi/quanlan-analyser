"""Generate research-modules manifests + registry from the Phase-1 feature ledger.

Single source of truth is docs/workspace-inventory (feature-ledger.csv and
traceability-matrix.csv). This registers every discovered module BEFORE any
algorithm is migrated, so feature counts stay reconcilable. It moves no code.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs" / "workspace-inventory"
MODULES_DIR = ROOT / "projects" / "research-modules" / "modules"
REGISTRY = ROOT / "projects" / "research-modules" / "registry.json"
STABLE_BASELINE = "8c5a673"

MANIFEST_SCHEMA_VERSION = "qlanalyser-module-manifest-v0.1"
REGISTRY_SCHEMA_VERSION = "qlanalyser-research-registry-v0.1"

# namespace -> (lifecycle default, implementation default, classification)
NAMESPACE_DEFAULTS = {
    "platform": ("stable", "implemented", "platform_capability"),
    "shared": ("stable", "implemented", "platform_capability"),
    "feature": ("beta", "implemented", "pluggable_feature_package"),
    "lab": ("draft", "implemented", "lab_demo_preview_teaching"),
    "assets": ("stable", "implemented", "historical_backup_evidence"),
    "governance": ("stable", "implemented", "platform_capability"),
    "research": ("internal_validation", "implemented", "pure_research_algorithm"),
}

# Per-module overrides grounded in the ledger's own state column and the
# frontend descriptor statusLevel (preview vs enabled) and known flag-gating.
OVERRIDES = {
    # preview-only features are not enabled in the running shell
    "feature.tfr": {"lifecycle": "internal_validation"},
    "feature.pac-v1": {"lifecycle": "internal_validation"},
    "feature.pac-v2": {"lifecycle": "internal_validation"},
    "feature.connectivity": {"lifecycle": "internal_validation"},
    "feature.multitaper": {"lifecycle": "internal_validation"},
    "feature.reference-csd": {"lifecycle": "internal_validation"},
    # epilepsy flow is local + feature-flag gated, not generally enabled
    "feature.epilepsy": {"lifecycle": "internal_validation"},
    "feature.epilepsy-ml": {"lifecycle": "internal_validation"},
    # qeeg version is 0.2.0; still Lab per plan
    "research.qeeg-64ch": {"lifecycle": "internal_validation", "version": "0.2.0"},
    # spike is planning-only
    "research.spike-analysis": {
        "lifecycle": "draft",
        "implementation": "placeholder",
        "classification": "placeholder_planned",
    },
}

ORIGIN_BY_NAMESPACE_PREFIX = {
    "research.qeeg-64ch": "qeeg-64ch-research",
    "research.spike-analysis": "spike-analysis",
}

SCOPE_DEFAULTS = {
    "platform": "Platform capability of the Web product shell. Not a scientific estimator.",
    "shared": "Shared computational or IO foundation reused by feature packages after cross-checked verification.",
    "feature": "Pluggable analysis feature package intended to mount into the Web shell.",
    "lab": "Lab / demo / preview / teaching surface. Not a validated production estimator.",
    "assets": "Static research evidence and delivered artifacts. Not runnable analysis code.",
    "governance": "Documentation and governance material for the platform.",
    "research": "Higher-maturity research method library; Lab-grade, not a clinical conclusion.",
}

FORBIDDEN_BY_NAMESPACE = {
    "feature": [
        "Do not present Lab/Beta output as a stable or clinical conclusion.",
        "Do not merge distinct estimator/profile semantics under one stable id.",
    ],
    "lab": [
        "Do not present demo/preview output as validated or clinical.",
        "Do not treat synthetic sample data as real subject evidence.",
    ],
    "research": [
        "Do not extrapolate 19-channel norms to 64-channel norms.",
        "Do not present Lab/recovered methods as stable clinical conclusions.",
        "Do not report AUTO_PASS_BLOCKED / blocked_ica_fit as an automatic pass.",
    ],
    "platform": ["Do not claim analysis validity; platform layer does no scientific estimation."],
    "shared": ["Do not claim standalone scientific validity; verify per consuming estimator."],
    "assets": ["Do not treat static evidence as current re-verified results."],
    "governance": ["Do not treat documentation as executable or verified behavior."],
}


def namespace_of(module_id: str) -> str:
    prefix = module_id.split(".", 1)[0]
    return prefix if prefix in NAMESPACE_DEFAULTS else "platform"


def slug_of(module_id: str) -> str:
    return module_id.replace(".", "__")


def load_traceability() -> dict[str, dict[str, str]]:
    with (INVENTORY / "traceability-matrix.csv").open(encoding="utf-8") as handle:
        return {row["module_id"]: row for row in csv.DictReader(handle)}


def origin_paths_for(module_id: str) -> list[str]:
    """Compact provenance: distinct top directories of the module's source files."""
    dirs: set[str] = set()
    with (INVENTORY / "feature-ledger.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["module_id"] != module_id:
                continue
            path = row["source_path"].replace("\\", "/")
            if not path or ":" in path.split("/", 1)[0]:
                continue
            parts = path.split("/")
            dirs.add("/".join(parts[:4]) if len(parts) >= 4 else path)
    return sorted(dirs)[:24] or [f"(no file paths recorded for {module_id})"]


def layer_state(present: bool, *, planned: bool = False) -> dict[str, str]:
    if present:
        return {"state": "present"}
    return {"state": "planned"} if planned else {"state": "not_applicable"}


def split_paths(cell: str) -> list[str]:
    return [p.strip() for p in cell.split("|") if p.strip()] if cell else []


def build_manifest(module_id: str, trace: dict[str, str]) -> dict:
    namespace = namespace_of(module_id)
    lifecycle, implementation, classification = NAMESPACE_DEFAULTS[namespace]
    version = "0.1.0"
    override = OVERRIDES.get(module_id, {})
    lifecycle = override.get("lifecycle", lifecycle)
    implementation = override.get("implementation", implementation)
    classification = override.get("classification", classification)
    version = override.get("version", version)

    domain = split_paths(trace.get("domain", ""))
    api = split_paths(trace.get("api", ""))
    service = split_paths(trace.get("service", ""))
    worker = split_paths(trace.get("worker", ""))
    frontend = split_paths(trace.get("frontend", ""))
    report = split_paths(trace.get("report", ""))
    tests_evidence = split_paths(trace.get("tests_evidence", ""))
    backend_paths = api + service + worker

    origin_project = ORIGIN_BY_NAMESPACE_PREFIX.get(module_id, "web-main")

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "module_id": module_id,
        "display_name": module_id,
        "namespace": namespace,
        "version": version,
        "lifecycle_status": lifecycle,
        "implementation_status": implementation,
        "source_provenance": {
            "origin_project": origin_project,
            "origin_paths": origin_paths_for(module_id),
            "migration_state": "registered_only",
        },
        "layers": {
            "domain": {"state": "present", "paths": domain} if domain else layer_state(False),
            "backend": {"state": "present", "paths": backend_paths} if backend_paths else layer_state(False),
            "frontend": {"state": "present", "paths": frontend} if frontend else layer_state(False),
            "report": {"state": "present", "paths": report} if report else layer_state(False),
            "tests": {"state": "present", "paths": tests_evidence} if tests_evidence else layer_state(False),
            "evidence": layer_state(False, planned=True),
        },
        "entry_points": {
            "frontend_pages": frontend,
            "api_routes": api,
            "services": service,
            "worker_runners": worker,
            "domain_runners": domain,
        },
        "scientific_scope": {
            "scope": SCOPE_DEFAULTS[namespace],
            "forbidden_claims": FORBIDDEN_BY_NAMESPACE[namespace],
            "customer_whitelist_allowed": False,
        },
        "verification": {
            "test_paths": tests_evidence,
            "evidence_paths": [],
            "last_verified_commit": STABLE_BASELINE,
        },
    }
    return manifest, classification


def main() -> int:
    traceability = load_traceability()
    MODULES_DIR.mkdir(parents=True, exist_ok=True)

    registry_modules = []
    for module_id in sorted(traceability):
        if module_id == "unclassified":
            continue
        manifest, classification = build_manifest(module_id, traceability[module_id])
        slug = slug_of(module_id)
        module_path = MODULES_DIR / slug
        module_path.mkdir(parents=True, exist_ok=True)
        manifest_file = module_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        registry_modules.append(
            {
                "module_id": module_id,
                "namespace": manifest["namespace"],
                "manifest_path": manifest_file.relative_to(ROOT).as_posix(),
                "lifecycle_status": manifest["lifecycle_status"],
                "implementation_status": manifest["implementation_status"],
                "classification": classification,
            }
        )

    unclassified = sum(1 for m in registry_modules if not m.get("classification"))
    registry = {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "generated_at_utc": "2026-07-22T00:00:00+00:00",
        "stable_baseline_commit": STABLE_BASELINE,
        "modules": registry_modules,
        "unclassified_count": unclassified,
    }
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"modules": len(registry_modules), "unclassified": unclassified}))
    return 1 if unclassified else 0


if __name__ == "__main__":
    raise SystemExit(main())
