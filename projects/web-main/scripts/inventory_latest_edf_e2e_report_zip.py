import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E2E_EVIDENCE = ROOT / "work" / "release_evidence" / "edf_upload_to_results_ui_only" / "edf_upload_to_results_ui_only.json"
OUT_DIR = ROOT / "work" / "release_evidence" / "edf_e2e_report_zip_inventory"
OUT_JSON = OUT_DIR / "edf_e2e_report_zip_inventory.json"
OUT_MD = OUT_DIR / "edf_e2e_report_zip_inventory.md"

REQUIRED_ENTRIES = [
    "reports/report.json",
    "reports/report.html",
    "reports/report.pdf",
    "reports/report_manifest.json",
]

REQUIRED_MODULES = ["psd", "erp", "tfr", "pac"]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    evidence = json.loads(E2E_EVIDENCE.read_text(encoding="utf-8"))
    downloads = evidence.get("downloads", [])
    report_download = next((item for item in downloads if item.get("requirement") == "report package zip"), None)
    if not report_download:
        raise SystemExit("missing report package zip download in EDF E2E evidence")
    zip_path = Path(str(report_download.get("path", "")))
    if not zip_path.exists():
        raise SystemExit(f"report zip does not exist: {zip_path}")

    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(zf.namelist())
        report = json.loads(zf.read("reports/report.json").decode("utf-8"))
        manifest = json.loads(zf.read("reports/report_manifest.json").decode("utf-8"))
        included = report.get("included_analyses", [])
        module_names = sorted({str(item.get("module_name", "")).lower() for item in included})
        analysis_prefixes = sorted({
            name.split("/")[1]
            for name in names
            if name.startswith("analyses/") and len(name.split("/")) > 2
        })
        required_matrix = {entry: entry in names for entry in REQUIRED_ENTRIES}
        module_matrix = {module: module in module_names for module in REQUIRED_MODULES}
        accidental_help_entries = [name for name in names if name.strip().lower() == "--help"]

    result = {
        "status": "passed",
        "evidence_path": str(E2E_EVIDENCE),
        "report_zip_path": str(zip_path),
        "report_zip_exists": zip_path.exists(),
        "report_zip_bytes": zip_path.stat().st_size,
        "entry_count": len(names),
        "required_entry_matrix": required_matrix,
        "required_module_matrix": module_matrix,
        "analysis_prefixes": analysis_prefixes,
        "included_analyses": included,
        "manifest_contract_version": manifest.get("contract_version"),
        "accidental_help_entries": accidental_help_entries,
        "missing_required_entries": [key for key, ok in required_matrix.items() if not ok],
        "missing_required_modules": [key for key, ok in module_matrix.items() if not ok],
    }
    if result["missing_required_entries"] or result["missing_required_modules"] or accidental_help_entries:
        result["status"] = "failed"

    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "\n".join([
            "# EDF E2E Report ZIP Inventory",
            "",
            f"- status: `{result['status']}`",
            f"- report zip: `{result['report_zip_path']}`",
            f"- entries: `{result['entry_count']}`",
            f"- required entries missing: `{result['missing_required_entries']}`",
            f"- required modules missing: `{result['missing_required_modules']}`",
            f"- accidental --help entries: `{result['accidental_help_entries']}`",
            f"- analysis prefixes: `{result['analysis_prefixes']}`",
            "",
        ]),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
