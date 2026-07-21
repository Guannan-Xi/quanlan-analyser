import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.main import app

FRONTEND_MAIN = ROOT / "frontend" / "app.js"
FRONTEND_HTML = ROOT / "frontend" / "index.html"
FRONTEND_CSS = ROOT / "frontend" / "styles.css"
RESEARCH_HTML = ROOT / "frontend" / "research-modules.html"
RESEARCH_JS = ROOT / "frontend" / "research-modules.js"
RESEARCH_MANIFEST = ROOT / "frontend" / "assets" / "research-modules" / "reproducibility" / "research_module_manifest.json"
ACCEPTANCE_JSON = ROOT / "work" / "acceptance" / "v01_acceptance_latest.json"
STATIC_ACCEPTANCE_JSON = ROOT / "work" / "acceptance" / "research_modules_static_latest.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def no_mojibake(*texts: str) -> bool:
    markers = ["\ufffd", "\u00c3", "\u00c2", "\u00e2\u20ac", "\u9359", "\u93c2", "\u9366"]
    return not any(marker in text for text in texts for marker in markers)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def count_checks(summary: dict) -> int:
    checks = summary.get("checks", 0)
    if isinstance(checks, list):
        return len(checks)
    if isinstance(checks, int):
        return checks
    return 0


def iter_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for key, item in value.items():
            strings.extend(iter_strings(key))
            strings.extend(iter_strings(item))
        return strings
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(iter_strings(item))
        return strings
    return []


def has_manifest_suffix(manifest: dict, suffixes: tuple[str, ...]) -> bool:
    return any(value.lower().endswith(suffixes) for value in iter_strings(manifest))


def score_persona(name: str, threshold: float, checks: list[tuple[str, float, bool]]) -> dict:
    score = round(sum(weight for _, weight, ok in checks if ok), 4)
    return {
        "persona": name,
        "score": score,
        "threshold": threshold,
        "satisfied": score >= threshold,
        "details": [{"check": check, "weight": weight, "ok": bool(ok)} for check, weight, ok in checks],
    }


def build_context() -> dict:
    client = TestClient(app)
    main = read(FRONTEND_MAIN)
    html = read(FRONTEND_HTML)
    css = read(FRONTEND_CSS)
    research_html = read(RESEARCH_HTML)
    research_js = read(RESEARCH_JS)
    manifest = load_json(RESEARCH_MANIFEST)
    return {
        "main": main,
        "html": html,
        "css": css,
        "research_html": research_html,
        "research_js": research_js,
        "manifest": manifest,
        "acceptance": load_json(ACCEPTANCE_JSON),
        "static_acceptance": load_json(STATIC_ACCEPTANCE_JSON),
        "health": client.get("/api/health").json(),
        "readiness": client.get("/api/health/readiness").json(),
        "templates": client.get("/api/templates").json(),
        "wallet": client.get("/api/billing/wallet").json(),
    }


def main() -> None:
    c = build_context()
    acceptance_checks = count_checks(c["acceptance"])
    static_acceptance_checks = count_checks(c["static_acceptance"])
    manifest_text = json.dumps(c["manifest"], ensure_ascii=False)
    combined = "\n".join([c["main"], c["html"], c["css"], c["research_html"], c["research_js"], manifest_text])
    research_combined = "\n".join([c["research_html"], c["research_js"]])
    templates = {item.get("id") for item in c["templates"]}
    disabled = set(c["readiness"].get("disabled_workflows", []))
    manifest_modules = set(c["manifest"].get("modules", {}))
    known_limits = c["readiness"].get("known_v01_limits", [])
    reproducibility_text = "\n".join([research_combined, manifest_text]).lower()
    personas = [
        score_persona("Research Customer", 0.90, [
            ("real_flow_buttons", 0.18, all(x in c["main"] for x in [
                'data-real-action="create-project"', 'data-real-action="upload-eeg"', 'data-real-action="run-qc"',
                'data-real-action="run-psd"', 'data-real-action="run-erp"', 'data-real-action="create-report"'])),
            ("workflow_ids", 0.18, all(x in c["main"] for x in ["metadata_qc", "resting_psd", "erp_p300"])),
            ("report_package_download", 0.16, "/reports/${report.id}/package" in c["main"]),
            ("research_modules_entry", 0.16, "research-modules" in c["research_html"] and "research-module/qc.html" in c["research_html"]),
            ("guardrail", 0.16, all(x in combined.lower() for x in ["clinical diagnosis", "synthetic", "research"])),
            ("clean_text", 0.16, no_mojibake(combined)),
        ]),
        score_persona("Backend API Integrator", 0.92, [
            ("health_ok", 0.14, c["health"].get("status") == "ok"),
            ("readiness_ready", 0.18, c["readiness"].get("status") == "ready"),
            ("enabled_templates", 0.18, {"metadata_qc", "resting_psd", "erp_p300"}.issubset(templates)),
            ("advanced_disabled", 0.18, {"tfr_ersp_itc", "pac_cfc", "connectivity"}.issubset(disabled)),
            ("billing_honest", 0.14, c["wallet"].get("enabled") is False),
            ("acceptance_passed", 0.18, c["acceptance"].get("status") == "passed" and acceptance_checks >= 120),
        ]),
        score_persona("Research Module Reviewer", 0.92, [
            ("six_modules", 0.18, {"qc", "psd", "erp", "tfr", "pac", "connectivity"}.issubset(manifest_modules)),
            ("enabled_vs_preview", 0.18, all(c["manifest"].get("modules", {}).get(slug, {}).get("status") for slug in manifest_modules)),
            ("downloads", 0.16, has_manifest_suffix(c["manifest"], (".csv",)) and has_manifest_suffix(c["manifest"], (".zip",))),
            ("reproducibility", 0.18, all(x in reproducibility_text for x in ["manifest", "method", "parameter", "reproducibility"])),
            ("static_acceptance", 0.16, c["static_acceptance"].get("status") == "passed" and static_acceptance_checks >= 120),
            ("clean_text", 0.14, no_mojibake(c["research_html"], c["research_js"])),
        ]),
        score_persona("Production Operator", 0.90, [
            ("storage_roots", 0.18, all(v.get("exists") and v.get("writable", True) for v in c["readiness"].get("storage_roots", {}).values())),
            ("state_registry", 0.18, c["readiness"].get("storage_roots", {}).get("state", {}).get("writable") is True),
            ("limits_visible", 0.16, all(x in known_limits for x in ["no clinical diagnosis", "no AI interpretation"])),
            ("output_contract", 0.16, "result.json" in c["acceptance"].get("results", [{}])[-1].get("detail", "") or acceptance_checks >= 180),
            ("no_blockers", 0.16, not c["readiness"].get("blockers")),
            ("clean_text", 0.16, no_mojibake(combined)),
        ]),
    ]
    summary = {"status": "passed" if all(p["satisfied"] for p in personas) else "failed", "personas": personas, "min_score": min(p["score"] for p in personas)}
    out = ROOT / "work" / "acceptance" / "v01_virtual_users_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
